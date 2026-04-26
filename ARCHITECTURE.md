# SovND-Project: Code Structure, Schema and Functionality

## Project Overview

**SovND** is an eBPF-based system monitoring and anomaly detection platform that traces syscalls at the kernel level and detects suspicious activity using signature matching, statistical analysis, and provenance graph heuristics.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Python User Space                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ebpf_agent.py   │  scoring/   │  graph/    │  detector/  │ metrics/ │ docker/│
│  (ctypes bridge) │ (Phase 5)   │ (Phase 5)  │  (Phase 4)  │ (Phase 4)│ (Phase 4)│
└──────────────┬───────────┼────────────┼─────────────┼──────────┼────────────┘
              │           │            │             │          │
              ▼           ▼            ▼             ▼          ▼
        ┌─────────────────────────────────────────────────────────┐
        │                 C Userspace Loader                      │
        │               (ebpf/loader.c shared lib)                │
        └──────────────────────────┬──────────────────────────────┘
                                   │ ctypes/CDLL
                                   ▼
        ┌─────────────────────────────────────────────────────────┐
        │                 eBPF Kernel Programs                    │
        │          (tracer.bpf.c, filter.bpf.c, etc.)             │
        └─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
sovnd-project/
├── src/
│   ├── ebpf_agent.py          # Python ctypes bridge to C library
│   ├── scoring/
│   │   └── engine.py        # Final suspicion score calculation (S >= T)
│   ├── graph/
│   │   └── builder.py       # Provenance Graph (NetworkX)
│   ├── detector/
│   │   ├── signature.py     # IOC-based pattern matching
│   │   └── statistical.py   # Z-score anomaly detection
│   ├── metrics/
│   │   └── engine.py        # EWMA + n-gram tracking
│   └── docker/
│       └── resolver.py      # Container metadata resolver
│
├── ebpf/
│   ├── loader.c             # libbpf loader (shared library)
│   ├── tracer.bpf.c         # Syscall tracepoint programs
│   ├── filter.bpf.c         # Filtering logic
│   ├── fd_tracker.bpf.c     # File descriptor tracking
│   ├── maps.bpf.h           # BPF map definitions
│   ├── vmlinux.h            # Kernel CO-RE headers
│   └── Makefile             # Build system
│
├── tests/                  # Automated test suite
├── deploy/                 # Deployment configs
└── data/                   # Runtime data (SQLite, logs)
```

## Phase History

| Phase | Commit | Description |
|-------|--------|------------|
| 1 | ba57fbf | Project initialization and skeleton |
| 2 | 48eeebc | Verified compilation and ignored object files |
| 3 | 4cf53f4 | Create Python eBPF agent bridge |
| 4 | 0e26ef4 | SignatureDetector + StatisticalDetector + MetricsEngine + ContainerResolver |
| 5 | 5d9f14a | ProvenanceGraphBuilder + ScoringEngine (S = sum(w_i * d_i) * P_ctx) |

---

## Module Documentation

### 1. src/graph/builder.py (Phase 5)

**Purpose**: Constructs a directed provenance graph for structural analysis.

**Key Features**:
- Uses **NetworkX** for graph representation.
- Nodes represent **Processes** and **Resources** (Files, Sockets).
- Edges represent **Actions** (open, read, write) with metadata.

**Methods**:
- `add_event(event)`: Updates the graph with new eBPF data.
- `get_process_subgraph(pid)`: Extracts the interaction neighborhood of a process.
- `get_serialized_graph()`: Exports graph in JSON format for UI visualization.

---

### 2. src/scoring/engine.py (Phase 5)

**Purpose**: Final decision engine that aggregates multiple detection signals.

**Formula**: 
33655 S = \sum (w_i \cdot d_i) \cdot P_{ctx} 33655

**Weights**:
- Signature Match: 15.0 (High Priority)
- Statistical Anomaly: 1.0 (Scaled by Z-score)
- Graph Heuristics: 5.0 (Structural triggers)

**Threshold**: $ T = 10.0 $ (Adjustable)

**Alert Structure**:
```python
@dataclass
class Alert:
    timestamp: str
    pid: int
    score: float
    severity: str  # info | warning | critical
    reasons: List[str]
    container_info: Optional[Dict]
```

---

### 3. src/ebpf_agent.py (Phase 3)

**Purpose**: Python ctypes bridge to kernel eBPF events

**Key Classes**:
- `Event`: ctypes Structure matching BPF event.
- `EBPFAgent`: Manages loader lifecycle and event polling thread.

---

### 4. src/detector/signature.py (Phase 4)

**Purpose**: Fast IOC-based detection using regex and pattern matching.
**Triggers**: /etc/shadow, /var/run/docker.sock, unauthorized shells.

---

### 5. src/detector/statistical.py (Phase 4)

**Purpose**: Evaluates Z-scores for scalar metrics (churn rate, FD count).

---

### 6. src/metrics/engine.py (Phase 4)

**Purpose**: EWMA-based metric tracking and n-gram frequency profiling.

---

### 7. src/docker/resolver.py (Phase 4)

**Purpose**: Maps cgroup_id to Docker container metadata with RLock-protected cache.

---

## Build & Test

```bash
# Build eBPF and Shared Lib
cd ebpf && make

# Run Tests
./venv/bin/pytest tests/
```
