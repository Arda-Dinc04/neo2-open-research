/* Receive-only vendor-interface identification. No USB OUT data, vendor
 * control requests, resets, driver detaches, alternate-setting changes,
 * set-configuration calls, or DJI command packets.
 * Claims one unbound vendor interface at a time, receives bounded IN data,
 * then releases it. This consumes endpoint data; it is not a bus sniffer.
 */
#include <libusb.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static long long millis(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void hex(const unsigned char *data, int length) {
    putchar('"');
    for (int i = 0; i < length; i++) printf("%02x", data[i]);
    putchar('"');
}

int main(int argc, char **argv) {
    int response_only = argc == 2 && strcmp(argv[1], "--receive-info-response-only") == 0;
    if (argc != 2 || (!response_only && strcmp(argv[1], "--receive-only") != 0)) return 2;
    libusb_context *ctx = NULL;
    int rc = libusb_init(&ctx);
    if (rc < 0) { printf("{\"init_error\":%d}\n", rc); return 2; }
    libusb_device **devices = NULL;
    ssize_t count = libusb_get_device_list(ctx, &devices);
    libusb_device *target = NULL;
    int matches = 0;
    for (ssize_t i = 0; i < count; i++) {
        struct libusb_device_descriptor descriptor;
        if (libusb_get_device_descriptor(devices[i], &descriptor) == 0 &&
            descriptor.idVendor == 0x2ca3 && descriptor.idProduct == 0x0020 &&
            descriptor.bcdDevice == 0x0504) {
            target = devices[i]; matches++;
        }
    }
    libusb_device_handle *handle = NULL;
    struct libusb_config_descriptor *cfg = NULL;
    int status = 3;
    printf("{\"mode\":\"receive_only\",\"response_followup\":%s,\"matching_devices\":%d", response_only ? "true" : "false", matches);
    if (matches != 1) goto finish;
    rc = libusb_open(target, &handle);
    printf(",\"open_result\":%d", rc);
    if (rc < 0) goto finish;
    int active = 0;
    rc = libusb_get_configuration(handle, &active);
    printf(",\"active_configuration\":%d,\"get_configuration_result\":%d", active, rc);
    if (rc < 0 || active != 1) goto finish;
    rc = libusb_get_active_config_descriptor(target, &cfg);
    if (rc < 0 || cfg->bNumInterfaces != 8) goto finish;
    unsigned char name[256];
    rc = libusb_get_string_descriptor_ascii(handle, cfg->iConfiguration, name, sizeof(name));
    const char expected[] = "rndis,mass_storage,bulk,acm";
    if (rc != (int)strlen(expected) || memcmp(name, expected, strlen(expected)) != 0) {
        printf(",\"configuration_string_verified\":false"); goto finish;
    }
    printf(",\"configuration_string_verified\":true,\"interface_strings\":[");
    for (int i = 0; i < 8; i++) {
        const struct libusb_interface *iface = &cfg->interface[i];
        if (i) printf(",");
        const struct libusb_interface_descriptor *alt = &iface->altsetting[0];
        int n = libusb_get_string_descriptor_ascii(handle, alt->iInterface, name, sizeof(name));
        printf("{\"number\":%u,\"string_index\":%u,\"result\":%d,\"ascii_hex\":",
               alt->bInterfaceNumber, alt->iInterface, n);
        hex(name, n > 0 ? n : 0); printf("}");
    }
    printf("],\"observations\":[");
    int first_number = response_only ? 4 : 3;
    int last_number = response_only ? 4 : 7;
    for (int number = first_number; number <= last_number; number++) {
        if (number != first_number) printf(",");
        printf("{\"interface\":%d", number);
        const struct libusb_interface *iface = &cfg->interface[number];
        if (iface->num_altsetting != 1) { printf(",\"guard_failed\":\"alternates\"}"); continue; }
        const struct libusb_interface_descriptor *alt = &iface->altsetting[0];
        unsigned char ep_in = (unsigned char)(0x81 + number);
        unsigned char ep_out = (unsigned char)number;
        int in_verified = 0, out_verified = 0;
        for (int e = 0; e < alt->bNumEndpoints; e++) {
            const struct libusb_endpoint_descriptor *ep = &alt->endpoint[e];
            if ((ep->bmAttributes & 3) != LIBUSB_TRANSFER_TYPE_BULK || ep->wMaxPacketSize != 512) continue;
            if (ep->bEndpointAddress == ep_in) in_verified++;
            if (ep->bEndpointAddress == ep_out) out_verified++;
        }
        if (alt->bInterfaceNumber != number || alt->bAlternateSetting != 0 ||
            alt->bInterfaceClass != 0xff || alt->bInterfaceSubClass != 0x43 ||
            alt->bInterfaceProtocol != 1 || alt->bNumEndpoints != 2 ||
            in_verified != 1 || out_verified != 1) {
            printf(",\"guard_failed\":\"descriptor_mismatch\"}"); continue;
        }
        int driver = libusb_kernel_driver_active(handle, number);
        printf(",\"kernel_driver_active_result\":%d", driver);
        if (driver != 0 && driver != LIBUSB_ERROR_NOT_SUPPORTED) {
            printf(",\"skipped\":\"driver_attached_or_unexpected_error\"}"); continue;
        }
        rc = libusb_claim_interface(handle, number);
        printf(",\"claim_result\":%d", rc);
        if (rc < 0) { printf("}"); continue; }
        int total = 0, timeouts = 0, read_error = 0, chunks = 0;
        long long start = millis(), deadline = start + (response_only ? 5000 : 1200);
        int byte_limit = response_only ? 1048576 : 16384;
        printf(",\"endpoint_in\":%u,\"chunks\":[", ep_in);
        while (millis() < deadline && total < byte_limit) {
            unsigned char buffer[512]; int transferred = 0;
            unsigned int timeout = (unsigned int)(deadline - millis());
            if (timeout == 0) break;
            if (timeout > 200) timeout = 200;
            rc = libusb_bulk_transfer(handle, ep_in, buffer, sizeof(buffer), &transferred, timeout);
            if (transferred > 0) {
                if (chunks++) printf(",");
                printf("{\"offset_ms\":%lld,\"hex\":", millis() - start);
                hex(buffer, transferred); printf("}"); total += transferred;
            }
            if (rc == LIBUSB_ERROR_TIMEOUT) timeouts++;
            else if (rc < 0) { read_error = rc; break; }
        }
        int release = libusb_release_interface(handle, number);
        printf("],\"bytes_received\":%d,\"timeouts\":%d,\"read_error\":%d,\"release_result\":%d}",
               total, timeouts, read_error, release);
    }
    printf("]"); status = 0;
finish:
    printf(",\"djicommand_bytes_sent\":0}\n");
    if (cfg) libusb_free_config_descriptor(cfg);
    if (handle) libusb_close(handle);
    if (devices) libusb_free_device_list(devices, 1);
    libusb_exit(ctx);
    return status;
}
