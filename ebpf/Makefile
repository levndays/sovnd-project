CLANG ?= clang
ARCH := $(shell uname -m | sed 's/x86_64/x86/' | sed 's/aarch64/arm64/')

BPF_CFLAGS := -target bpf -g -O2 -D__TARGET_ARCH_$(ARCH) \
              -I/usr/include/$(shell uname -m)-linux-gnu \
              -I.

all: libloader.so

tracer.bpf.o: tracer.bpf.c maps.bpf.h vmlinux.h
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

tracer.skel.h: tracer.bpf.o
	bpftool skeleton gen $< > $@

libloader.so: loader.c tracer.skel.h
	$(CLANG) -g -O2 -Wall -fPIC -shared loader.c -lbpf -lelf -lz -o $@

clean:
	rm -f *.o *.skel.h libloader.so
