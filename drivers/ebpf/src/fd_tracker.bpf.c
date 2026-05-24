// fd_tracker.bpf.c — FD lifecycle tracking helpers
// §1.3, §2.1: Track file descriptor open/close pairs,
// concurrent FD count (m₄), and FD type classification.

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include "maps.bpf.h"

static __always_inline __u64 make_fd_key(__u32 pid, __u32 fd) {
    return ((__u64)pid << 32) | (__u64)fd;
}

static __always_inline void track_fd_open(__u32 pid, __u32 fd, __u32 fd_type) {
    __u64 key = make_fd_key(pid, fd);
    struct fd_info info = {};
    info.fd_type = fd_type;
    info.open_ts = bpf_ktime_get_ns();
    bpf_map_update_elem(&fd_table, &key, &info, BPF_ANY);

    __u32 *count = bpf_map_lookup_elem(&proc_stats, &pid);
    if (count)
        __sync_fetch_and_add(count, 1);
}

static __always_inline void track_fd_close(__u32 pid, __u32 fd) {
    __u64 key = make_fd_key(pid, fd);
    bpf_map_delete_elem(&fd_table, &key);

    __u32 *count = bpf_map_lookup_elem(&proc_stats, &pid);
    if (count && *count > 0)
        __sync_fetch_and_sub(count, 1);
}

static __always_inline __u32 get_fd_type(__u32 pid, __u32 fd) {
    __u64 key = make_fd_key(pid, fd);
    struct fd_info *info = bpf_map_lookup_elem(&fd_table, &key);
    return info ? info->fd_type : FD_TYPE_UNKNOWN;
}

static __always_inline struct proc_stats *get_or_create_stats(__u32 pid) {
    struct proc_stats *s = bpf_map_lookup_elem(&proc_stats, &pid);
    if (!s) {
        struct proc_stats zero = {};
        bpf_map_update_elem(&proc_stats, &pid, &zero, BPF_ANY);
        s = bpf_map_lookup_elem(&proc_stats, &pid);
    }
    return s;
}
