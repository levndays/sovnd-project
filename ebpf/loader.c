#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <getopt.h>
#include <sys/resource.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include "tracer.skel.h"

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

int start_loader(event_cb_t cb)
{
    int err;

    user_callback = cb;
    libbpf_set_print(libbpf_print_fn);

    skel = tracer_bpf__open();
    if (!skel) {
        fprintf(stderr, "Failed to open BPF skeleton\n");
        return 1;
    }

    err = tracer_bpf__load(skel);
    if (err) {
        fprintf(stderr, "Failed to load BPF skeleton\n");
        goto cleanup;
    }

    err = tracer_bpf__attach(skel);
    if (err) {
        fprintf(stderr, "Failed to attach BPF skeleton\n");
        goto cleanup;
    }

    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) {
        err = -1;
        fprintf(stderr, "Failed to create ring buffer\n");
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
