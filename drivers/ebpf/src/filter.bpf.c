// filter.bpf.c — in-eBPF event filtering helpers
// §2.3: Three-layer filter: pre-eBPF (not here), in-eBPF (cgroup/PID/path),
// post-eBPF (done in Python).
//
// Implementation of:
//   1. Target cgroup matching
//   2. Path prefix noise filtering (/proc, /sys unless critical)
//   3. Per-PID rate limiting (sampling beyond threshold)

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include "maps.bpf.h"

#define RATE_LIMIT_DEFAULT  1000   // events/sec/pid before sampling
#define RATE_WINDOW_NS      1000000000ULL  // 1 second

static __always_inline int rate_check(__u32 pid) {
    struct rate_val *rv = bpf_map_lookup_elem(&event_rate, &pid);
    __u64 now = bpf_ktime_get_ns();

    if (!rv) {
        struct rate_val init = { .window_start_ns = now, .count = 1 };
        bpf_map_update_elem(&event_rate, &pid, &init, BPF_ANY);
        return 1; // allow
    }

    if (now - rv->window_start_ns > RATE_WINDOW_NS) {
        rv->window_start_ns = now;
        rv->count = 1;
        return 1; // new window, allow
    }

    __sync_fetch_and_add(&rv->count, 1);

    // Sample: if we're over limit, emit only every 10th event
    if (rv->count > RATE_LIMIT_DEFAULT) {
        return (rv->count % 10 == 0) ? 1 : 0;
    }

    return 1; // under limit, allow all
}

static __always_inline int should_skip_path(const char *filename) {
    // Noise reduction: skip high-churn system paths unless critical
    // /proc/self/ — frequent, low value for security monitoring
    #pragma unroll
    for (int i = 0; i < 10; i++) {
        if (filename[i] == '\0') break;
        if (i == 0 && filename[i] != '/') return 0;
    }
    // Skip /proc/* patterns except /proc/kcore
    if (filename[0] == '/' && filename[1] == 'p' && filename[2] == 'r' &&
        filename[3] == 'o' && filename[4] == 'c' && filename[5] == '/') {
        // Allow /proc/kcore (IOC)
        if (filename[6] == 'k' && filename[7] == 'c') return 0;
        return 1; // skip other /proc/*
    }
    // Skip /sys/* unless security-related
    if (filename[0] == '/' && filename[1] == 's' && filename[2] == 'y' &&
        filename[3] == 's' && filename[4] == '/') {
        return 1;
    }
    return 0; // allow
}

static __always_inline int filter_event(__u32 pid, __u64 cgroup_id, const char *filename) {
    // Check filter_config for target cgroup restriction
    struct filter_key fk = { .idx = 0 };
    struct filter_val *fv = bpf_map_lookup_elem(&filter_config, &fk);
    if (fv && fv->enabled && fv->target_cgroup != 0) {
        // Only emit events from the target cgroup
        if (fv->target_cgroup != cgroup_id)
            return 0;
    }

    if (should_skip_path(filename))
        return 0;

    return rate_check(pid);
}
