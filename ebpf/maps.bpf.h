#ifndef __MAPS_BPF_H
#define __MAPS_BPF_H

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>

/* Ring buffer for sending events to user space */
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

/* Hash map for storing process metrics in kernel space */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32);   /* PID */
    __type(value, __u64); /* Metric counter (e.g., syscall count) */
} proc_metrics SEC(".maps");

/* Map to store container ID (cgroup id) to metadata mapping if needed */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u64);   /* cgroup id */
    __type(value, __u32); /* Placeholder for metadata/flags */
} container_map SEC(".maps");

#endif /* __MAPS_BPF_H */
