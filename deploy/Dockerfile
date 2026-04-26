# Stage 1: Build Stage
FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y \
    clang llvm libbpf-dev make gcc libc6-dev-i386 bpftool linux-headers-generic

WORKDIR /build
COPY ebpf/ .
RUN make clean && make all

# Stage 2: Runtime Stage
FROM python:3.12-slim

# System dependencies for eBPF and performance
RUN apt-get update && apt-get install -y \
    libbpf1 libelf1 zlib1g procps curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ensure data directory exists for volume mounting
RUN mkdir -p /app/data && chmod 777 /app/data

# Python Dependency Management
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Artifact Deployment
COPY --from=builder /build/libloader.so /app/ebpf/
COPY --from=builder /build/tracer.bpf.o /app/ebpf/
COPY src/ /app/src/

# Environment Configuration
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Healthcheck to verify API availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Robust Entrypoint
RUN echo '#!/bin/bash\n\
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &\n\
streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000 8501
CMD ["/app/entrypoint.sh"]
