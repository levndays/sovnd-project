// tracer.bpf.c — eBPF probe for SovND runtime security monitoring
// §2.3: Attaches to tracepoints for FD-level behavioral profiling.
// Hooks: openat (enter+exit), close, read, write, socket (enter+exit), pipe2 (enter+exit)
//
// Captured metrics per process (m₁–m₄ per §2.1):
//   m₁ — fd churn rate (open/close events)
//   m₂ — FD type distribution (file/socket/pipe)
//   m₃ — I/O intensity (bytes read/written)
//   m₄ — concurrent FD count (open minus close)

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>
#include "maps.bpf.h"
#include "filter.bpf.c"
#include "fd_tracker.bpf.c"

char LICENSE[] SEC("license") = "GPL";

static __always_inline __u32 get_tid(void) {
    return (__u32)bpf_get_current_pid_tgid();
}

static __always_inline __u32 get_pid(void) {
    return (__u32)(bpf_get_current_pid_tgid() >> 32);
}

static __always_inline int submit_event(struct event *e) {
    void *buf = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
    if (!buf) return 0;
    __builtin_memcpy(buf, e, sizeof(*e));
    bpf_ringbuf_submit(buf, 0);
    return 1;
}

// ── openat ──────────────────────────────────────────────────────────
// On sys_enter_openat we capture the filename to pair with the
// returned FD on sys_exit_openat.

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    __u32 tid = get_tid();
    __u32 pid = get_pid();
    __u64 cgroup_id = bpf_get_current_cgroup_id();

    struct pending_val pv = { .fd_type = FD_TYPE_FILE };
    bpf_probe_read_user_str(&pv.filename, sizeof(pv.filename),
                            (const char *)ctx->args[1]);

    if (!filter_event(pid, cgroup_id, pv.filename))
        return 0;

    bpf_map_update_elem(&pending_open, &tid, &pv, BPF_ANY);
    return 0;
}

SEC("tracepoint/syscalls/sys_exit_openat")
int trace_openat_exit(struct trace_event_raw_sys_exit *ctx) {
    __u32 tid = get_tid();
    __u32 pid = get_pid();
    __s64 ret = ctx->ret;
    if (ret < 0) return 0; // open failed
    __u32 fd = (__u32)ret;

    struct pending_val *pv = bpf_map_lookup_elem(&pending_open, &tid);
    if (!pv) return 0;

    track_fd_open(pid, fd, FD_TYPE_FILE);

    struct proc_stats *stats = get_or_create_stats(pid);
    if (stats) __sync_fetch_and_add(&stats->open_count, 1);

    struct event e = {};
    e.pid = pid;
    e.tgid = tid;
    e.cgroup_id = bpf_get_current_cgroup_id();
    e.op_type = EVT_OP_OPEN;
    e.fd = fd;
    e.fd_type = FD_TYPE_FILE;
    e.timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    __builtin_memcpy(e.filename, pv->filename, sizeof(e.filename));

    bpf_map_delete_elem(&pending_open, &tid);
    submit_event(&e);
    return 0;
}

// ── close ───────────────────────────────────────────────────────────

SEC("tracepoint/syscalls/sys_enter_close")
int trace_close(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = get_pid();
    __u32 fd = (__u32)ctx->args[0];
    if (fd <= 2) return 0; // skip stdin/stdout/stderr

    struct proc_stats *stats = get_or_create_stats(pid);
    if (stats) __sync_fetch_and_add(&stats->close_count, 1);

    __u32 fd_type = get_fd_type(pid, fd);
    track_fd_close(pid, fd);

    struct event e = {};
    e.pid = pid;
    e.tgid = get_tid();
    e.cgroup_id = bpf_get_current_cgroup_id();
    e.op_type = EVT_OP_CLOSE;
    e.fd = fd;
    e.fd_type = fd_type;
    e.timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    submit_event(&e);
    return 0;
}

// ── read ────────────────────────────────────────────────────────────

SEC("tracepoint/syscalls/sys_enter_read")
int trace_read(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = get_pid();
    __u32 fd = (__u32)ctx->args[0];
    __u64 count = ctx->args[2];
    if (fd <= 2 || count == 0) return 0;

    struct proc_stats *stats = get_or_create_stats(pid);
    if (stats) __sync_fetch_and_add(&stats->read_bytes, count);

    __u32 fd_type = get_fd_type(pid, fd);

    struct event e = {};
    e.pid = pid;
    e.tgid = get_tid();
    e.cgroup_id = bpf_get_current_cgroup_id();
    e.op_type = EVT_OP_READ;
    e.fd = fd;
    e.fd_type = fd_type;
    e.bytes = count;
    e.timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    submit_event(&e);
    return 0;
}

// ── write ───────────────────────────────────────────────────────────

SEC("tracepoint/syscalls/sys_enter_write")
int trace_write(struct trace_event_raw_sys_enter *ctx) {
    __u32 pid = get_pid();
    __u32 fd = (__u32)ctx->args[0];
    __u64 count = ctx->args[2];
    if (fd <= 2 || count == 0) return 0;

    struct proc_stats *stats = get_or_create_stats(pid);
    if (stats) __sync_fetch_and_add(&stats->write_bytes, count);

    __u32 fd_type = get_fd_type(pid, fd);

    struct event e = {};
    e.pid = pid;
    e.tgid = get_tid();
    e.cgroup_id = bpf_get_current_cgroup_id();
    e.op_type = EVT_OP_WRITE;
    e.fd = fd;
    e.fd_type = fd_type;
    e.bytes = count;
    e.timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    submit_event(&e);
    return 0;
}

// ── socket ──────────────────────────────────────────────────────────

SEC("tracepoint/syscalls/sys_enter_socket")
int trace_socket(struct trace_event_raw_sys_enter *ctx) {
    __u32 tid = get_tid();
    struct pending_val pv = { .fd_type = FD_TYPE_SOCKET };
    bpf_map_update_elem(&pending_open, &tid, &pv, BPF_ANY);
    return 0;
}

SEC("tracepoint/syscalls/sys_exit_socket")
int trace_socket_exit(struct trace_event_raw_sys_exit *ctx) {
    __u32 tid = get_tid();
    __u32 pid = get_pid();
    __s64 ret = ctx->ret;
    if (ret < 0) {
        bpf_map_delete_elem(&pending_open, &tid);
        return 0;
    }
    __u32 fd = (__u32)ret;

    struct pending_val *pv = bpf_map_lookup_elem(&pending_open, &tid);
    if (!pv) return 0;

    track_fd_open(pid, fd, FD_TYPE_SOCKET);

    struct proc_stats *stats = get_or_create_stats(pid);
    if (stats) __sync_fetch_and_add(&stats->open_count, 1);

    struct event e = {};
    e.pid = pid;
    e.tgid = tid;
    e.cgroup_id = bpf_get_current_cgroup_id();
    e.op_type = EVT_OP_OPEN;
    e.fd = fd;
    e.fd_type = FD_TYPE_SOCKET;
    e.timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&e.comm, sizeof(e.comm));

    bpf_map_delete_elem(&pending_open, &tid);
    submit_event(&e);
    return 0;
}

// ── pipe2 ───────────────────────────────────────────────────────────

SEC("tracepoint/syscalls/sys_enter_pipe2")
int trace_pipe2(struct trace_event_raw_sys_enter *ctx) {
    __u32 tid = get_tid();
    struct pending_val pv = { .fd_type = FD_TYPE_PIPE };
    bpf_map_update_elem(&pending_open, &tid, &pv, BPF_ANY);
    return 0;
}

SEC("tracepoint/syscalls/sys_exit_pipe2")
int trace_pipe2_exit(struct trace_event_raw_sys_exit *ctx) {
    __u32 tid = get_tid();
    __u32 pid = get_pid();
    __s64 ret = ctx->ret;
    if (ret < 0) {
        bpf_map_delete_elem(&pending_open, &tid);
        return 0;
    }

    struct pending_val *pv = bpf_map_lookup_elem(&pending_open, &tid);
    if (!pv) return 0;
    bpf_map_delete_elem(&pending_open, &tid);

    // pipe2 returns 0 on success; the two FDs are written
    // to userspace memory at ctx->args[0]. We can't easily
    // extract them from a tracepoint, so emit a synthetic
    // event without FD numbers for pipe creation tracking.
    struct proc_stats *stats = get_or_create_stats(pid);
    if (stats) __sync_fetch_and_add(&stats->open_count, 2);

    struct event e = {};
    e.pid = pid;
    e.tgid = tid;
    e.cgroup_id = bpf_get_current_cgroup_id();
    e.op_type = EVT_OP_OPEN;
    e.fd_type = FD_TYPE_PIPE;
    e.timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&e.comm, sizeof(e.comm));
    submit_event(&e);
    return 0;
}
