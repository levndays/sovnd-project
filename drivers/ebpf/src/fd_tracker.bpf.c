#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include "maps.bpf.h"

// Logic for tracking open FDs
