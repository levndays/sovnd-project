#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include "maps.bpf.h"

// Logic for dropping events from non-target PIDs
// This can be expanded with more complex filtering rules
