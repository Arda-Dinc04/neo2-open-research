/* Continuous receive-only Neo 2 DUML source.
 * The sole bulk transfer endpoint is literal IN 0x85. No USB OUT payload,
 * vendor request, configuration/alternate-setting change, reset, or driver
 * detach is implemented. Standard descriptor reads identify the interface.
 * Temporary claiming consumes endpoint data; this is not a USB bus sniffer.
 */
#include <libusb.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static volatile sig_atomic_t stopping = 0;

static void stop_handler(int signum) {
    (void)signum;
    stopping = 1;
}

static long long monotonic_ms(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static void error_event(const char *stage, int code) {
    printf("{\"type\":\"error\",\"stage\":\"%s\",\"code\":%d}\n", stage, code);
}

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "--receive-only") != 0) {
        fprintf(stderr, "Usage: usb_stream --receive-only\n");
        return 2;
    }
    setvbuf(stdout, NULL, _IOLBF, 0);
    signal(SIGINT, stop_handler);
    signal(SIGTERM, stop_handler);
#ifdef SIGPIPE
    signal(SIGPIPE, stop_handler);
#endif
    libusb_context *context = NULL;
    libusb_device **devices = NULL;
    libusb_device_handle *handle = NULL;
    struct libusb_config_descriptor *configuration = NULL;
    int claimed = 0, status = 3, rc;
    long long started = monotonic_ms();
    unsigned long long received = 0, transfers = 0;

    rc = libusb_init(&context);
    if (rc < 0) { error_event("libusb_init", rc); goto cleanup; }
    ssize_t count = libusb_get_device_list(context, &devices);
    if (count < 0) { error_event("device_list", (int)count); goto cleanup; }
    libusb_device *target = NULL;
    int matches = 0;
    for (ssize_t i = 0; i < count; i++) {
        struct libusb_device_descriptor descriptor;
        if (libusb_get_device_descriptor(devices[i], &descriptor) == 0 &&
            descriptor.idVendor == 0x2ca3 && descriptor.idProduct == 0x0020) {
            target = devices[i];
            matches++;
        }
    }
    if (matches != 1) { error_event("unique_device_required", matches); goto cleanup; }
    rc = libusb_open(target, &handle);
    if (rc < 0) { error_event("device_open", rc); goto cleanup; }
    int active_configuration = 0;
    rc = libusb_get_configuration(handle, &active_configuration);
    if (rc < 0 || active_configuration != 1) {
        error_event("active_configuration_1_required", rc < 0 ? rc : active_configuration);
        goto cleanup;
    }
    rc = libusb_get_active_config_descriptor(target, &configuration);
    if (rc < 0) { error_event("configuration_descriptor", rc); goto cleanup; }
    if (configuration->bConfigurationValue != 1 || configuration->bNumInterfaces != 8) {
        error_event("configuration_layout", -1); goto cleanup;
    }
    const char expected[] = "rndis,mass_storage,bulk,acm";
    unsigned char text[256];
    rc = libusb_get_string_descriptor_ascii(handle, configuration->iConfiguration,
                                           text, sizeof(text));
    if (rc != (int)strlen(expected) || memcmp(text, expected, strlen(expected)) != 0) {
        error_event("configuration_function_string", -1); goto cleanup;
    }
    const struct libusb_interface_descriptor *selected = NULL;
    for (int i = 0; i < configuration->bNumInterfaces; i++) {
        const struct libusb_interface *interface = &configuration->interface[i];
        for (int a = 0; a < interface->num_altsetting; a++) {
            const struct libusb_interface_descriptor *alt = &interface->altsetting[a];
            if (alt->bInterfaceNumber == 4 && alt->bAlternateSetting == 0) {
                if (selected || interface->num_altsetting != 1) {
                    error_event("ambiguous_interface", -1); goto cleanup;
                }
                selected = alt;
            }
        }
    }
    if (!selected || selected->bInterfaceClass != 0xff ||
        selected->bInterfaceSubClass != 0x43 || selected->bInterfaceProtocol != 1 ||
        selected->bNumEndpoints != 2) {
        error_event("interface_4_layout", -1); goto cleanup;
    }
    int verified_in = 0, verified_pair = 0;
    for (int i = 0; i < selected->bNumEndpoints; i++) {
        const struct libusb_endpoint_descriptor *endpoint = &selected->endpoint[i];
        if ((endpoint->bmAttributes & 3) != LIBUSB_TRANSFER_TYPE_BULK ||
            endpoint->wMaxPacketSize != 512) continue;
        if (endpoint->bEndpointAddress == 0x85) verified_in++;
        if (endpoint->bEndpointAddress == 0x04) verified_pair++;
    }
    if (verified_in != 1 || verified_pair != 1) {
        error_event("endpoint_layout", -1); goto cleanup;
    }
    rc = libusb_kernel_driver_active(handle, 4);
    if (rc != 0 && rc != LIBUSB_ERROR_NOT_SUPPORTED) {
        error_event("driver_attached_or_unknown", rc); goto cleanup;
    }
    rc = libusb_claim_interface(handle, 4);
    if (rc < 0) { error_event("interface_claim", rc); goto cleanup; }
    claimed = 1;
    printf("{\"type\":\"ready\",\"interface\":4,\"endpoint_in\":\"0x85\","
           "\"read_only\":true,\"sensor_clock_verified\":false}\n");
    status = 0;
    while (!stopping) {
        unsigned char buffer[16384];
        int transferred = 0;
        /* Literal IN endpoint: there is no bulk OUT call in this program. */
        rc = libusb_bulk_transfer(handle, 0x85, buffer, sizeof(buffer), &transferred, 200);
        if (transferred > 0) {
            printf("{\"type\":\"transfer\",\"interface\":4,\"endpoint_in\":\"0x85\","
                   "\"elapsed_ms\":%lld,\"bytes\":%d,\"hex\":\"",
                   monotonic_ms() - started, transferred);
            for (int i = 0; i < transferred; i++) printf("%02x", buffer[i]);
            printf("\"}\n");
            received += (unsigned)transferred;
            transfers++;
        }
        if (rc < 0 && rc != LIBUSB_ERROR_TIMEOUT && rc != LIBUSB_ERROR_INTERRUPTED) {
            error_event("bulk_in", rc); status = 4; break;
        }
        if (ferror(stdout)) break;
    }
cleanup:
    if (claimed) {
        rc = libusb_release_interface(handle, 4);
        if (rc < 0) { error_event("interface_release", rc); status = 4; }
    }
    if (configuration) libusb_free_config_descriptor(configuration);
    if (handle) libusb_close(handle);
    if (devices) libusb_free_device_list(devices, 1);
    if (context) libusb_exit(context);
    printf("{\"type\":\"end\",\"bytes_received\":%llu,\"transfers\":%llu,"
           "\"application_bytes_sent\":0,\"exit_code\":%d}\n", received, transfers, status);
    return status;
}
