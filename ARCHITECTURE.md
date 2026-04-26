# SovND-Project: Code Structure, Schema and Functionality

## Project Overview

**SovND** (Security of Virtualized Network Devices) is a high-performance, eBPF-powered security monitoring platform. It implements a hybrid detection model combining real-time syscall tracing, statistical anomaly detection (Z-score/EWMA), signature-based IOC matching, and provenance graph analysis.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            User Space (Python 3.12)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Dashboard    │      API      │    Scoring    │    Graph    │   Detectors   │
│ (Streamlit)   │   (FastAPI)   │    Engine     │   Builder   │ (Stat/Sig)    │
└───────┬───────┴───────┬───────┴───────┬───────┴───────┬─────┴───────┬───────┘
        │               │               │               │             │
        │       ┌───────▼───────────────▼───────────────▼─────────────▼────┐
        │       │             Persistence Layer (SQLite 3)                 │
        │       └───────────────────────┬──────────────────────────────────┘
        │                               │
        └───────────────────────────────┼──────────────────────────────────┐
                                        ▼                                  │
        ┌─────────────────────────────────────────────────────────┐        │
        │                 eBPF Loader & Bridge                    │        │
        │            (loader.c shared lib via ctypes)             │        │
        └──────────────────────────┬──────────────────────────────┘        │
                                   │                                       │
        ┌──────────────────────────▼──────────────────────────────┐        │
        │                 Kernel Space (eBPF)                     │        │
        │      (Tracepoints, Ring Buffers, Shared Maps)           │        │
        └─────────────────────────────────────────────────────────┘        │
                                   │                                       │
                                   ▼                                       │
        ┌─────────────────────────────────────────────────────────┐        │
        │                Target Docker Containers                 │◄───────┘
        │            (Traced via cgroup_id & PID)                 │
        └─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
sovnd-project/
├── src/
│   ├── api/
│   │   └── main.py          # FastAPI REST Interface & Prometheus Metrics
│   ├── dashboard/
│   │   └── app.py           # Streamlit UI (Plotly, Agraph)
│   ├── storage/
│   │   └── sqlite.py        # Persistence for Alerts & Profiles
│   ├── scoring/
│   │   └── engine.py        # Final Decision Logic (S >= T)
│   ├── graph/
│   │   └── builder.py       # Provenance Graph Constructor (NetworkX)
│   ├── detector/
│   │   ├── signature.py     # Regex/IOC Pattern Matcher
│   │   └── statistical.py   # Z-score Anomaly Detection
│   ├── metrics/
│   │   └── engine.py        # EWMA & n-gram Profile Engine
│   ├── docker/
│   │   └── resolver.py      # cgroup_id to Container Metadata Resolver
│   └── ebpf_agent.py        # Core Python Bridge (ctypes)
│
├── ebpf/
│   ├── tracer.bpf.c         # Core eBPF tracing logic
│   ├── loader.c             # C-side libbpf loader
│   ├── Makefile             # CO-RE Build system
│   └── vmlinux.h            # Kernel types for CO-RE
│
├── tests/                  # Pytest suite
├── deploy/                 # Docker/Compose deployment files
└── data/                   # SQLite database (sovnd.db)
```

## Core Modules Documentation

### 1. Dashboard (src/dashboard/app.py)
**Purpose**: High-fidelity visual interface for security analysts.
- **Real-time Monitoring**: Plotly charts for alert severity distribution.
- **Incident Management**: Dataframes for historical alert review.
- **Graph Visualization**: Interactive `streamlit-agraph` implementation of the provenance graph.

### 2. API & Metrics (src/api/main.py)
**Purpose**: External data access and observability.
- **REST Endpoints**: `/api/alerts`, `/api/status`.
- **Prometheus**: `/metrics` endpoint for scraping syscall counts and alert rates.

### 3. Scoring Engine (src/scoring/engine.py)
**Purpose**: Multi-signal fusion to minimize False Positives.
- **Algorithm**: $ S = \sum (w_i \cdot d_i) \cdot P_{ctx} $
- **Severity Classification**: Automatic mapping from suspicion score to Alert object.

### 4. Storage Manager (src/storage/sqlite.py)
**Purpose**: Thread-safe persistence.
- **Schema**: Tables for `profiles` (blob mu/sigma) and `alerts` (json reasons).
- **Concurrency**: Uses `threading.Lock` and context-managed connections.

### 5. eBPF Tracer (ebpf/tracer.bpf.c)
**Purpose**: Low-overhead kernel-level instrumentation.
- **Events**: Intercepts `openat`, `close`, etc.
- **Data Transfer**: Uses high-performance `BPF_MAP_TYPE_RINGBUF`.

---

## Technical Specifications

| Component | Technology |
|-----------|------------|
| Kernel Tracing | eBPF (CO-RE) |
| Binary Interface | libbpf / C / ctypes |
| Data Analysis | NumPy / NetworkX |
| Web Framework | FastAPI |
| Dashboard | Streamlit |
| Database | SQLite 3 |
| Serialization | JSON / Pickle |

## Build and Execution

### Build Artifacts
```bash
cd ebpf && make
# Produces: tracer.bpf.o, tracer.skel.h, libloader.so
```

### Run System
```bash
# Start API
./venv/bin/uvicorn src.api.main:app --port 8000

# Start Dashboard
./venv/bin/streamlit run src/dashboard/app.py
```

### Verification
```bash
./venv/bin/pytest tests/
```
