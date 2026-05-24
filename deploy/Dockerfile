# Stage 1: Build Stage
FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y \
    clang llvm libbpf-dev make gcc libc6-dev-i386 bpftool linux-headers-generic \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY drivers/ebpf/ ./ebpf/
RUN cd ebpf && make clean && make all

# Stage 2: Runtime Stage
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libbpf1 libelf1 zlib1g procps curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/data && chmod 777 /app/data

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --from=builder /build/ebpf/libloader.so    /app/drivers/ebpf/
COPY --from=builder /build/ebpf/tracer.bpf.o    /app/drivers/ebpf/

COPY apps/       /app/apps/
COPY core/       /app/core/
COPY internal/   /app/internal/
COPY web/        /app/web/
COPY scripts/    /app/scripts/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

RUN printf '#!/bin/bash\n\
python3 -m uvicorn apps.server:app --host 0.0.0.0 --port 8000 &\n\
PID1=$!\n\
sleep 2\n\
python3 apps/agent.py\n\
wait $PID1\n' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000
CMD ["/app/entrypoint.sh"]
