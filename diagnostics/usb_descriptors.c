/* Optional libusb inspection. Default: cached descriptors only, no open/claim.
 * --read-descriptors additionally opens the device and allows ONLY standard
 * USB GET_DESCRIPTOR (0x80/0x06), bounded to 4096 bytes and a 1000 ms timeout.
 * No set-configuration, interface claim, reset, vendor requests or bulk I/O.
 */
#include <libusb.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int read_descriptor(libusb_device_handle *handle, uint8_t type,
                            uint8_t index, uint16_t lang) {
    unsigned char bytes[4096];
    int count = libusb_control_transfer(handle, 0x80, 0x06,
        ((uint16_t)type << 8) | index, lang, bytes, sizeof(bytes), 1000);
    printf("{\"descriptor_type\":%u,\"index\":%u,\"result\":%d,\"hex\":\"", type, index, count);
    for (int i = 0; i < count; i++) printf("%02x", bytes[i]);
    printf("\"}");
    return count >= 0 ? 0 : 1;
}

int main(int argc, char **argv) {
    int active = argc == 2 && strcmp(argv[1], "--read-descriptors") == 0;
    if (argc > 1 && !active) {
        fprintf(stderr, "Usage: usb_descriptors [--read-descriptors]\n");
        return 2;
    }
    libusb_context *ctx = NULL;
    int rc = libusb_init(&ctx);
    if (rc < 0) {
        printf("{\"error\":\"libusb_init\",\"code\":%d}\n", rc);
        return 2;
    }
    libusb_device **list = NULL;
    ssize_t count = libusb_get_device_list(ctx, &list);
    if (count < 0) {
        printf("{\"error\":\"libusb_get_device_list\",\"code\":%ld}\n", (long)count);
        libusb_exit(ctx);
        return 2;
    }
    int found = 0, first_device = 1, errors = 0;
    printf("{\"mode\":\"%s\",\"visible_device_count\":%ld,\"devices\":[",
           active ? "standard_GET_DESCRIPTOR" : "cached_descriptors", (long)count);
    for (ssize_t d = 0; d < count; d++) {
        struct libusb_device_descriptor dev;
        rc = libusb_get_device_descriptor(list[d], &dev);
        if (rc < 0) { errors++; continue; }
        if (dev.idVendor != 0x2ca3 || dev.idProduct != 0x0020) continue;
        found++;
        if (!first_device) printf(",");
        first_device = 0;
        printf("{\"vid\":%u,\"pid\":%u,\"bus\":%u,\"address\":%u,\"configurations\":[",
               dev.idVendor, dev.idProduct, libusb_get_bus_number(list[d]),
               libusb_get_device_address(list[d]));
        for (uint8_t ci = 0; ci < dev.bNumConfigurations; ci++) {
            if (ci) printf(",");
            struct libusb_config_descriptor *cfg = NULL;
            rc = libusb_get_config_descriptor(list[d], ci, &cfg);
            if (rc < 0) {
                printf("{\"error\":\"get_config_descriptor\",\"code\":%d}", rc);
                errors++;
                continue;
            }
            printf("{\"configuration_value\":%u,\"configuration_string_index\":%u,\"interfaces\":[",
                   cfg->bConfigurationValue, cfg->iConfiguration);
            int first_iface = 1;
            for (uint8_t ii = 0; ii < cfg->bNumInterfaces; ii++) {
                const struct libusb_interface *iface = &cfg->interface[ii];
                for (int ai = 0; ai < iface->num_altsetting; ai++) {
                    const struct libusb_interface_descriptor *alt = &iface->altsetting[ai];
                    if (!first_iface) printf(",");
                    first_iface = 0;
                    printf("{\"number\":%u,\"alternate\":%u,\"class\":%u,\"subclass\":%u,\"protocol\":%u,\"endpoints\":[",
                           alt->bInterfaceNumber, alt->bAlternateSetting,
                           alt->bInterfaceClass, alt->bInterfaceSubClass, alt->bInterfaceProtocol);
                    for (uint8_t ei = 0; ei < alt->bNumEndpoints; ei++) {
                        const struct libusb_endpoint_descriptor *ep = &alt->endpoint[ei];
                        if (ei) printf(",");
                        printf("{\"address\":%u,\"direction\":\"%s\",\"transfer_type\":%u,\"max_packet_size\":%u}",
                               ep->bEndpointAddress, (ep->bEndpointAddress & 0x80) ? "IN" : "OUT",
                               ep->bmAttributes & 3, ep->wMaxPacketSize);
                    }
                    printf("]}");
                }
            }
            printf("]}");
            libusb_free_config_descriptor(cfg);
        }
        printf("]");
        if (active) {
            libusb_device_handle *handle = NULL;
            rc = libusb_open(list[d], &handle);
            printf(",\"open_result\":%d", rc);
            if (rc == 0) {
                printf(",\"read_results\":[");
                errors += read_descriptor(handle, LIBUSB_DT_DEVICE, 0, 0);
                for (uint8_t ci = 0; ci < dev.bNumConfigurations; ci++) {
                    printf(",");
                    errors += read_descriptor(handle, LIBUSB_DT_CONFIG, ci, 0);
                }
                /* Read the supported LANGID, then each configuration string.
                 * Configuration names can distinguish multiple DJI bulk uses.
                 * No guessed language or guessed functional mapping is used.
                 */
                unsigned char langs[255];
                int n = libusb_control_transfer(handle, 0x80, 0x06,
                    LIBUSB_DT_STRING << 8, 0, langs, sizeof(langs), 1000);
                if (n >= 4 && langs[1] == LIBUSB_DT_STRING) {
                    uint16_t lang = (uint16_t)langs[2] | ((uint16_t)langs[3] << 8);
                    for (uint8_t ci = 0; ci < dev.bNumConfigurations; ci++) {
                        struct libusb_config_descriptor *cfg = NULL;
                        if (libusb_get_config_descriptor(list[d], ci, &cfg) == 0) {
                            if (cfg->iConfiguration) {
                                printf(",");
                                errors += read_descriptor(handle, LIBUSB_DT_STRING,
                                    cfg->iConfiguration, lang);
                            }
                            libusb_free_config_descriptor(cfg);
                        }
                    }
                } else {
                    printf(",{\"descriptor_type\":3,\"index\":0,\"result\":%d}", n);
                    errors++;
                }
                printf("]");
                libusb_close(handle);
            } else errors++;
        }
        printf("}");
    }
    printf("],\"found\":%d,\"errors\":%d}\n", found, errors);
    libusb_free_device_list(list, 1);
    libusb_exit(ctx);
    /* No match is inconclusive about the physical connection under a sandbox. */
    return found && !errors ? 0 : 3;
}
