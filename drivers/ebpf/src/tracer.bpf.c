#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>
#include "maps.bpf.h"

char LICENSE[] SEC("license") = "GPL";

struct event {
    __u32 pid;
    __u32 tgid;
    __u64 cgroup_id;
    __u32 syscall_id;
    char comm[16];
    char filename[256];
};

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    struct event *e;
    __u64 id = bpf_get_current_pid_tgid();
    __u32 pid = id >> 32;

    // 1. Check metric counters FIRST, before reserving memory
    __u64 *count, one = 1;
    count = bpf_map_lookup_elem(&proc_metrics, &pid);
    
    if (count) {
        __sync_fetch_and_add(count, 1);
        
        // 2. KERNEL KILL SWITCH: Process is going rogue (e.g., crawler)
        if (*count > 5000) {
            bpf_send_signal(9); // Instantly send SIGKILL from kernel space
            return 0; // Discard event, kill process
        }
        
        // 3. RATE LIMITING: Stop flooding Python after 100 events
        if (*count > 100) {
            return 0; // Silently drop event from ring buffer to save CPU
        }
    } else {
        bpf_map_update_elem(&proc_metrics, &pid, &one, BPF_ANY);
    }

    // 4. Reserve buffer and send to user-space (Python)
    e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
    if (!e) return 0;

    e->pid = pid;
    e->tgid = id;
    e->cgroup_id = bpf_get_current_cgroup_id();
    e->syscall_id = 257; // openat
    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    
    const char *pathname = (const char *)ctx->args[1];
    bpf_probe_read_user_str(&e->filename, sizeof(e->filename), pathname);
    
    bpf_ringbuf_submit(e, 0);

    return 0;
}

SEC("tracepoint/syscalls/sys_enter_close")
int trace_close(struct trace_event_raw_sys_enter *ctx) {
    // Similar logic for close
    return 0;
}
