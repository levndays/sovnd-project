# Stage 1: Build eBPF and C-Loader
FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y \
    clang \
    llvm \
    libbpf-dev \
    make \
    gcc \
    libc6-dev-i386 \
    linux-headers-generic \
    bpftool

WORKDIR /build
COPY ebpf/ .
# Note: In a real build, we'd need to handle vmlinux.h generation or provide it
# Since we generated it on the host, we copy it.
RUN make clean && make all

# Stage 2: Runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libbpf1 \
    libelf1 \
    zlib1g \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy compiled artifacts from builder
COPY --from=builder /build/libloader.so ./ebpf/
COPY --from=builder /build/tracer.bpf.o ./ebpf/

# Copy application source
COPY src/ ./src/
COPY data/ ./data/

# Expose ports for API (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Entry point script to run both API and Dashboard
cat <<EOT > entrypoint.sh
#!/bin/bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
EOT

RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
