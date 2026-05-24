#ifndef __MAPS_BPF_H__
#define __MAPS_BPF_H__

#include <bpf/bpf_helpers.h>

enum {
    EVT_OP_OPEN  = 1,
    EVT_OP_CLOSE = 2,
    EVT_OP_READ  = 3,
    EVT_OP_WRITE = 4,
};

enum {
    FD_TYPE_FILE   = 1,
    FD_TYPE_SOCKET = 2,
    FD_TYPE_PIPE   = 3,
    FD_TYPE_ANON   = 4,
    FD_TYPE_UNKNOWN = 0,
};

struct event {
    __u32 pid;
    __u32 tgid;
    __u64 cgroup_id;
    __u32 op_type;
    __u32 fd;
    __u32 fd_type;
    __u64 bytes;
    __u64 timestamp_ns;
    char comm[16];
    char filename[256];
};

struct pending_val {
    char filename[256];
    __u32 fd_type;
};

struct fd_info {
    __u32 fd_type;
    __u64 open_ts;
};

struct proc_stats {
    __u32 fd_count;       // m4 — concurrent open FDs
    __u64 open_count;     // for churn rate m1
    __u64 close_count;    // for churn rate m1
    __u64 read_bytes;     // for I/O intensity m3
    __u64 write_bytes;    // for I/O intensity m3
    __u64 last_event_ns;
};

struct rate_val {
    __u64 window_start_ns;
    __u32 count;
};

struct filter_key {
    __u32 idx;
};

struct filter_val {
    __u64 target_cgroup;
    __u32 rate_limit;    // max events per second per PID
    __u32 enabled;
    char path_prefix[64];
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32);
    __type(value, struct proc_stats);
} proc_stats SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 65536);
    __type(key, __u64);
    __type(value, struct fd_info);
} fd_table SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, struct pending_val);
} pending_open SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32);
    __type(value, struct rate_val);
} event_rate SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1);
    __type(key, struct filter_key);
    __type(value, struct filter_val);
} filter_config SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u64);
    __type(value, __u32);
} container_map SEC(".maps");

#endif
