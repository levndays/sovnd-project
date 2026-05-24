CLANG ?= clang
ARCH := $(shell uname -m | sed 's/x86_64/x86/' | sed 's/aarch64/arm64/')

BPF_CFLAGS := -target bpf -g -O2 -D__TARGET_ARCH_$(ARCH) \
              -I/usr/include/$(shell uname -m)-linux-gnu \
              -Iinclude

all: libloader.so

tracer.bpf.o: src/tracer.bpf.c include/maps.bpf.h include/vmlinux.h
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

tracer.skel.h: tracer.bpf.o
	bpftool gen skeleton $< > $@

libloader.so: loader/loader.c tracer.skel.h
	$(CLANG) -g -O2 -Wall -fPIC -shared $< -lbpf -lelf -lz -o $@ -I.

clean:
	rm -f *.o *.skel.h libloader.so
