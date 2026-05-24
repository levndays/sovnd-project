CLANG ?= clang
ARCH := $(shell uname -m | sed 's/x86_64/x86/' | sed 's/aarch64/arm64/')

BPF_CFLAGS := -target bpf -g -O2 -D__TARGET_ARCH_$(ARCH) \
              -I/usr/include/$(shell uname -m)-linux-gnu \
              -Iinclude -Isrc \
              -mllvm -bpf-stack-size=4096

PIN_DIR := /sys/fs/bpf/sovnd

all: libloader.so

tracer.bpf.o: src/tracer.bpf.c src/filter.bpf.c src/fd_tracker.bpf.c include/maps.bpf.h include/vmlinux.h
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

tracer.skel.h: tracer.bpf.o
	bpftool gen skeleton $< > $@

libloader.so: loader/loader.c tracer.skel.h
	$(CLANG) -g -O2 -Wall -fPIC -shared $< -lbpf -lelf -lz -o $@ -I.

pin:
	mkdir -p $(PIN_DIR)
	bpftool map create $(PIN_DIR)/rb       type ringbuf key 0 value 0 entries 262144 name rb || true
	bpftool map create $(PIN_DIR)/proc_stats type hash key 4 value 40 entries 10240 name proc_stats || true

clean:
	rm -f *.o tracer.skel.h libloader.so
	rm -rf $(PIN_DIR)

.PHONY: all clean pin
