CLANG ?= clang
LLC ?= llc
ARCH := $(shell uname -m | sed 's/x86_64/x86/' | sed 's/aarch64/arm64/')

BPF_CFLAGS := -target bpf -g -O2 -D__TARGET_ARCH_$(ARCH) \
              -I/usr/include/$(shell uname -m)-linux-gnu \
              -I.

all: tracer.bpf.o

tracer.bpf.o: tracer.bpf.c maps.bpf.h vmlinux.h
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

clean:
	rm -f *.o
