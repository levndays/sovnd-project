#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include "tracer.skel.h"

#define PIN_DIR "/sys/fs/bpf/sovnd"

static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
{
    return vfprintf(stderr, format, args);
}

struct tracer_bpf *skel;
struct ring_buffer *rb = NULL;

typedef void (*event_cb_t)(void *ctx, void *data, size_t size);
event_cb_t user_callback = NULL;

static int handle_event(void *ctx, void *data, size_t data_sz)
{
    if (user_callback) {
        user_callback(ctx, data, data_sz);
    }
    return 0;
}

int pin_maps(void)
{
    int err;
    mkdir(PIN_DIR, 0755);

    err = bpf_map__pin(skel->maps.rb, PIN_DIR "/rb");
    if (err) fprintf(stderr, "[loader] rb pin: %s\n", strerror(-err));

    err = bpf_map__pin(skel->maps.proc_stats, PIN_DIR "/proc_stats");
    if (err) fprintf(stderr, "[loader] proc_stats pin: %s\n", strerror(-err));

    err = bpf_map__pin(skel->maps.fd_table, PIN_DIR "/fd_table");
    if (err) fprintf(stderr, "[loader] fd_table pin: %s\n", strerror(-err));

    err = bpf_map__pin(skel->maps.event_rate, PIN_DIR "/event_rate");
    if (err) fprintf(stderr, "[loader] event_rate pin: %s\n", strerror(-err));

    err = bpf_map__pin(skel->maps.filter_config, PIN_DIR "/filter_config");
    if (err) fprintf(stderr, "[loader] filter_config pin: %s\n", strerror(-err));

    err = bpf_map__pin(skel->maps.container_map, PIN_DIR "/container_map");
    if (err) fprintf(stderr, "[loader] container_map pin: %s\n", strerror(-err));

    return 0;
}

int start_loader(event_cb_t cb)
{
    int err;

    user_callback = cb;
    libbpf_set_print(libbpf_print_fn);

    skel = tracer_bpf__open();
    if (!skel) {
        fprintf(stderr, "[loader] Failed to open BPF skeleton\n");
        return 1;
    }

    err = tracer_bpf__load(skel);
    if (err) {
        fprintf(stderr, "[loader] Failed to load BPF skeleton\n");
        goto cleanup;
    }

    err = tracer_bpf__attach(skel);
    if (err) {
        fprintf(stderr, "[loader] Failed to attach BPF skeleton\n");
        goto cleanup;
    }

    pin_maps();

    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) {
        err = -1;
        fprintf(stderr, "[loader] Failed to create ring buffer\n");
        goto cleanup;
    }

    return 0;

cleanup:
    tracer_bpf__destroy(skel);
    return err;
}

int poll_events(int timeout_ms)
{
    return ring_buffer__poll(rb, timeout_ms);
}

void stop_loader()
{
    ring_buffer__free(rb);
    tracer_bpf__destroy(skel);
}
