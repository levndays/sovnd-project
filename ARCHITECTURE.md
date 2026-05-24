# SovND - Kernel-Level Security Monitoring & Explainable Scoring

## Project Overview

**SovND** (pronounced "sovereign") is a real-time Linux kernel security monitoring system that combines eBPF-based syscall tracing with multi-vectors detection (signature, statistical, and provenance graph analysis) to generate explainable threat scores.

### Key Features
- **eBPF Kernel Tracing** - Zero-overhead syscall capture via `tracepoint/syscalls`
- **Explainable Scoring** - Three-component formula: `S = Σ(w_i × d_i)`
- **Multi-Vector Detection** - Signature + Statistical + Graph heuristics
- **Live Dashboard** - WebSocket telemetry with Chart.js visualization
- **SQLite Persistence** - Alert storage for historical analysis

### Motivation
Traditional HIDS agents (AIDE, OSSEC) scan periodically, missing transient threats. Commercial solutions (CrowdStrike, SentinelOne) are expensive and opaque. SovND provides an open-source, kernel-level alternative with mathematically explainable scoring.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD (Browser)                         │
│              Chart.js + WebSocket (web/index.html)
└───────────────────────────────┬─────────────────────────────────────┘
                              │ ws://localhost:8000/ws/telemetry
┌───────────────────────────────▼─────────────────────────────────────┐
│                    API SERVER (FastAPI)                           │
│              apps/server.py (Uvicorn on port 8000)
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────────┐   │
│  │ WebSocket      │  │ /api/attack   │  │ SQLite Query      │   │
│  │ Telemetry     │  │ Trigger      │  │ Endpoint        │   │
│  └───────────────┘  └──────────────┘  └─────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────┘
                             │ storage.save_alert()
┌───────────────────────────▼───────────────────────────────────────┐
│              STORAGE LAYER (SQLite)                            │
│                   data/sovnd.db                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │ alerts: id, timestamp, pid, comm, score, severity,  │     │
│  │        reasons (JSON), breakdown (JSON)             │     │
│  └─────────────────────────────────────────────────────┘     │
└───────────────────────────────┬────────────���────────────────────────┘
                             │ get_recent_alerts()
┌───────────────────────────▼───────────────────────────────────────┐
│              MAIN AGENT LOOP (Python)                          │
│              apps/agent.py                              │
│  ┌─────────────────────────────────────────────────┐           │
│  │  ScoringEngine                           │           │
│  │  compute(event, stat_report,      │           │
│  │  sig_match, graph_heuristics)         │           │
│  │  → Alert(score, breakdown, reasons)  │           │
│  └─────────────────────────────────────────────────┘           │
│                        ▲                                     │
│    ┌──────────────────┬┴───────────────────┐              │
│    │              DETECTORS                  │              │
│ ┌──▼──────────┐ ┌─────▼───────┐ ┌─────────▼────────┐     │
│ │ Signature   │ │ Statistical │ │ Graph          │     │
│ │ Detector   │ │ Detector   │ │ Builder       │     │
│ │ (regex IOC) │ │ (z-scores) │ │ (provenance)  │     │
│ └────────────┘ └───────────┘ └────────────────┘     │
│                        │                                │
└────────────────────────┼────────────────────────────────┘
                         │ get_event()
┌───────────────────────▼────────────────────────────────┐
│              eBPF AGENT (Python ctypes)                    │
│              drivers/ebpf/bridge.py                           │
│  ┌─────────────────────────────────────────────┐       │
│  │ C Library Loader (ebpf/libloader.so)        │       │
│  │ - start_loader()                         │       │
│  │ - poll_events(timeout_ms)                │       │
│  │ - stop_loader()                       │       │
│  └─────────────────────────────────────────────┘       │
└───────────────────────────────┬────────────────────────────────┘
                             │ tracepoint/syscalls
┌───────────────────────────▼────────────────────────────────┐
│              LINUX KERNEL (eBPF)                        │
│         drivers/ebpf/src/tracer.bpf.c            │
│  ┌─────────────────────────────────────────────┐       │
│  │ trace_openat() - sys_enter_openat          │       │
│  │ trace_close() - sys_enter_close           │       │
│  │ ring buffer for events                   │       │
│  └───���─────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────┘
```

---

## Components

### 1. eBPF Kernel Tracer (`drivers/ebpf/src/tracer.bpf.c`)

**Purpose:** Capture syscalls directly from the kernel with zero process overhead.

**Implementation:**
- Two tracepoint hooks: `sys_enter_openat` and `sys_enter_close`
- Uses BPF ring buffer (`rb`) for efficient event delivery
- CO-RE (Compile Once Run Everywhere) for kernel BTF compatibility

**Data Captured:**
| Field | Type | Description |
|-------|------|------------|
| `pid` | u32 | Process ID |
| `tgid` | u32 | Thread Group ID |
| `cgroup_id` | u64 | Control Group ID |
| `op_type` | u32 | Operation type (1=OPEN, 2=CLOSE, 3=READ, 4=WRITE) |
| `fd_type` | u32 | File descriptor type (1=FILE, 2=SOCKET, 3=PIPE) |
| `comm` | char[16] | Process command name |
| `filename` | char[256] | File path |
| `bytes` | u64 | Bytes transferred (read/write) |

**Key Code:**
```c
// tracer.bpf.c (simplified)
SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    // Load filename from RDI register (first arg)
    bpf_probe_read_user(&data.filename, sizeof(data.filename), (void *)ctx->args[1]);
    // Store in ring buffer
    bpf_ringbuf_output(&rb, &data, sizeof(data), 0);
    return 0;
}
```

**Build Command:**
```bash
clang -target bpf -g -O2 -Idrivers/ebpf -c drivers/ebpf/src/tracer.bpf.c -o drivers/ebpf/tracer.bpf.o
```

---

### 2. eBPF Agent (`drivers/ebpf/bridge.py`)

**Purpose:** Python bridge to the compiled eBPF object via shared library.

**Key Responsibilities:**
1. Load C library via `ctypes.CDLL`
2. Register Python callback for ring buffer events
3. Poll events in background thread
4. Expose `get_event(timeout)` API to main loop

**Event Structure (Python):**
```python
{
    "pid": int,
    "tgid": int,
    "cgroup_id": int,
    "op_type": int,     # 1=OPEN, 2=CLOSE, 3=READ, 4=WRITE
    "op_name": str,     # "open", "close", "read", "write"
    "fd": int,
    "fd_type": int,     # 1=FILE, 2=SOCKET, 3=PIPE
    "fd_type_name": str,
    "bytes": int,
    "timestamp_ns": int,
    "comm": str,        # e.g., "sudo", "python3"
    "filename": str     # e.g., "/etc/shadow"
}
```

---

### 3. Signature Detector (`core/detection/signature.py`)

**Purpose:** Fast pattern matching against known IOCs (Indicators of Compromise).

**Detection Logic:**

```python
class SignatureDetector:
    # Critical file access (IOCs)
    critical_paths = [
        r'^/etc/shadow$',        # Password hashes
        r'^/etc/sudoers$',      # sudo config
        r'^/var/run/docker\.sock$',  # Docker socket
        r'^/root/.ssh/.*',      # SSH keys
        r'^/proc/kcore$'        # Kernel memory
    ]
    
    # Suspicious processes
    suspicious_comm = ["bash", "sh", "nc", "ncat", "python", "perl"]
```

**Decision Rationale:**
- Regex patterns are O(n) where n = number of paths (5), inherently fast
- Critical files are high-confidence IOCs - false positives acceptable
- Suspicious comm detection guards against reverse shells and lateral movement

---

### 4. Statistical Detector (`core/detection/statistical.py`)

**Purpose:** Learn process behavior and detect statistical anomalies using Z-scores.

**Mathematical Model:**
- **EWMA (Exponentially Weighted Moving Average):** `μ_t = α × x_t + (1-α) × μ_{t-1}`
- **Z-score:** `z = (x - μ) / σ`
- **Anomaly threshold:** `|z| > threshold_z` (default 3.0)

**Implementation:**
```python
z_scores = engine.get_z_scores(pid, current_vector)
max_z = np.max(np.abs(z_scores))
is_anomalous = max_z > self.threshold_z
```

**Why EWMA?**
- Adapts to concept drift (process behavior changes over time)
- Memory-efficient (only stores μ and σ, not full history)
- Configurable via α (default 0.3 = 30% weight on recent samples)

**Design Decision:** In demo mode, statistical scores are randomized (25% chance, z ∈ [2.5, 8.5]) because real attacks would build baseline profiles first - new processes have no history.

---

### 5. Metrics Engine (`core/metrics/engine.py`)

**Purpose:** Maintains per-PID behavioral profiles.

**Profile Structure (per PID):**
The `_Profile` class uses `__slots__` for memory efficiency:

| Attribute | Type | Description |
|-----------|------|-------------|
| `mu` | List[float] (7) | EWMA mean vector |
| `sigma` | List[float] (7) | EWMA standard deviation |
| `window` | Deque[List[float]] | Last N metric snapshots |
| `ngram_buf` | Deque[int] | Last N syscall op types |
| `ngram_counts` | Dict[Tuple[int,...], int] | N-gram frequency counts |

**Feature Vector (7-dimensional):**
| Index | Feature | Description |
|-------|---------|-------------|
| 0 | m1_fd_churn | FD open + close events / sec |
| 1 | m2_file_frac | Fraction of FILE FDs |
| 2 | m2_sock_frac | Fraction of SOCKET FDs |
| 3 | m2_pipe_frac | Fraction of PIPE FDs |
| 4 | m3_read_bps | Bytes read / sec |
| 5 | m3_write_bps | Bytes written / sec |
| 6 | m4_fd_count | Concurrent open FD count |

**Design Decision:** Feature vector captures FD lifecycle and I/O patterns. Real implementations would also include: CPU usage, memory delta, network bytes, disk I/O rate, etc.

---

### 6. Graph Builder (`core/graph/builder.py`)

**Purpose:** Construct process-to-resource provenance for lateral movement detection.

**Graph Structure:**
- **Nodes:** Process (`proc_{pid}`), File (`file_{path}`), Socket (`socket_{fd}`)
- **Directed Edges:** Process → Resource

**Heuristics Implemented:**
```python
# 1. High connectivity - processes touching many files
high_connectivity: subgraph.number_of_nodes() > 3

# 2. Sensitive access - /etc or /root files
sensitive_access: filename.startswith("/etc") or filename.startswith("/root")
```

**Graph Lib:** NetworkX (Python graph library)

**Design Decision:** Using NetworkX for rapid prototyping. Production would use GPUGraph or Graphistry for billion-node scale.

---

### 7. Scoring Engine (`core/scoring/engine.py`)

**Purpose:** Combine all detection vectors into an explainable threat score.

**Scoring Formula:**
```
S = w_signature × sig_match + w_statistical × max_z + w_graph × |heuristics|

where:
  w_signature = 15.0   (high - signature match is definitive)
  w_statistical = 1.0   (low - z-score is scaled)
  w_graph = 5.0         (medium - heuristics are suspicious)
```

**Score Breakdown:**
```python
breakdown = {
    "signature": 0.0 or 15.0,
    "statistical": max_z * 1.0,  # e.g., 5.2 if z=5.2
    "graph": len(heuristics) * 5.0  # e.g., 10.0 if 2 heuristics
}
```

**Alert Generation:**
```python
if total_score >= threshold:
    severity = "CRITICAL" if total_score > 20 else "WARNING"
    return Alert(
        score=total_score,
        severity=severity,
        breakdown=comp,
        reasons=[...]  # Human-readable
    )
```

**Threshold Decision:** Set to 15.0 to reduce false positives from graph-only alerts (sensitive_access alone is 5.0, below threshold).

---

### 8. Storage Layer (`internal/storage/sqlite.py`)

**Purpose:** Persist alerts for historical analysis.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP,
    pid INTEGER,
    comm TEXT,
    score REAL,
    severity TEXT,
    reasons TEXT,        -- JSON array
    breakdown TEXT      -- JSON object
)
```

**Design Decision:** Using SQLite (not PostgreSQL) for demo portability. Production would use TimescaleDB or ClickHouse.

---

### 9. API Server (`apps/server.py`)

**Purpose:** Web dashboard backend.

**Endpoints:**
| Path | Method | Description |
|------|--------|-------------|
| `/` | GET | Serve static/index.html |
| `/ws/telemetry` | WS | Stream {eps, alerts} at 2Hz |
| `/api/attack` | POST | Trigger demo attacks |

**WebSocket Message Format:**
```json
{
    "eps": 1500,  // events per second
    "alerts": [
        {
            "timestamp": "2026-04-27T10:30:00",
            "pid": 7390,
            "comm": "cat",
            "score": 17.5,
            "severity": "WARNING",
            "reasons": ["Access to critical file: /etc/shadow", "Statistical Anomaly (Z=2.5)"],
            "breakdown": {"signature": 15.0, "statistical": 2.5, "graph": 0.0}
        }
    ]
}
```

---

### 10. Dashboard (`web/index.html`)

**Purpose:** Browser UI for live telemetry.

**Features:**
- Chart.js line graph (throughput over 40 buckets)
- Alert stack with score breakdown (SIG/STAT/GRPH)
- "SIMULATE MULTI-STAGE ATTACK" button

**Key JavaScript (WebSocket):**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Update chart
    chart.data.datasets[0].data.push(data.eps);
    chart.data.datasets[0].data.shift();
    chart.update();
    
    // Show alerts (10s grace period for clock drift)
    const liveAlerts = data.alerts.filter(a => 
        new Date(a.timestamp).getTime() > sessionStartTime - 10000
    );
    
    // Render cards with breakdown
    alertList.innerHTML = liveAlerts.map(a => `
        <div>
            PID ${a.pid} [${a.comm}] 
            SCORE ${a.score}
            SIG: ${a.breakdown.signature}
            STAT: ${a.breakdown.statistical}
            GRPH: ${a.breakdown.graph}
        </div>
    `).join('');
}
```

**Design Decision:** WebSocket avoids polling overhead. Chart.js for zero-dependency charting.

---

## Demo Orchestrator (`apps/demo.py`)

**Purpose:** One-command launch for demos.

**Flow:**
```python
def start():
    # 1. Clean data/ for fresh start
    os.remove("data/sovnd.db")
    
    # 2. Start API server (port 8000)
    api_proc = subprocess.Popen(["uvicorn", "apps.server:app"])
    
    # 3. Start eBPF agent
    agent_proc = subprocess.Popen(["python3", "apps/agent.py"])
    
    # 4. Open browser
    os.system("xdg-open http://localhost:8000")
```

**Usage:**
```bash
sudo python3 apps/demo.py start
# Opens browser to http://localhost:8000
```

---

## Key Design Decisions

### 1. Why eBPF for tracing?
- **Kernel-level:** No userspace overhead, can't be evade by process hiding
- **Ring buffer:** Log(1) egress - no blocking
- **CO-RE:** Works across kernel versions without recompilation

### 2. Why three detection vectors?
| Vector | Strength | Weakness |
|--------|----------|---------|
| Signature | Zero false positive on IOCs | Misses novel attacks |
| Statistical | Catches deviations | Needs baseline first |
| Graph | Detects lateral movement | Computationally heavy |

**Multi-vector approach** ensures coverage across attack kill chain.

### 3. Why weighted sum scoring?
- Interpretability: Each component is explainable
- Tunability: Weights can be adjusted per environment
- Threshold is single knob for operators

### 4. Why SQLite for demo?
- No external dependency (PostgreSQL requires daemon)
- ACID compliance for alert integrity
- Easy export for further analysis

### 5. Why WebSocket over HTTP polling?
- 2Hz update rate needed for live feel
- Polling would double server load
- WebSocket is full-duplex

---

## Score Variations (Expected Output)

When running `sudo python3 demo.py start`:

| Scenario | SIG | STAT | GRPH | Total |
|----------|-----|------|------|-------|
| Signature only | 15.0 | 0.0 | 0.0 | **15.0** |
| SIG + sensitive_access | 15.0 | 0.0 | 5.0 | **20.0** |
| SIG + z-score 2.5 | 15.0 | 2.5 | 0.0 | **17.5** |
| SIG + z-score 8.5 | 15.0 | 8.5 | 0.0 | **23.5** |
| SIG + STAT + GRPH + z7.5 | 15.0 | 7.5 | 5.0 | **27.5** |

---

## Dependencies

### Python Packages
| Package | Version | Purpose |
|---------|---------|---------|
| numpy | 1.26.4 | Statistical calculations |
| networkx | 2.8.8 | Graph provenance |
| fastapi | - | Web API |
| uvicorn | - | ASGI server |
| websockets | - | WebSocket support |

### System Requirements
- Linux kernel 5.10+ (BTF support)
- Root access (CAP_BPF for eBPF)
- clang + llvm (eBPF compilation)

---

## Future Improvements

### Phase 2 (Production-Ready)
1. **Machine Learning:** Train classifier on labeled attack data
2. **Kafka Export:** Stream alerts to SIEM
3. **Horizontal Scaling:** DistributedAgents per host
4. **Graph Visualization:** Cytoscape.js for provenance

### Phase 3 (Enterprise)
1. **eBPFmaps:** Share state across agents
2. **Kernel Hardening:** SECCOMP policies
3. **Performance:** < 1% CPU overhead
4. **Compliance:** SOC2 audit logs

---

## Appendix: File Structure

```
sovnd-project/
├── apps/               # Entry points
│   ├── agent.py        # Main engine
│   ├── server.py       # API server
│   └── demo.py         # Demo orchestrator
├── core/               # Detection logic
│   ├── detection/      # Signature/Statistical
│   ├── graph/          # Provenance graph
│   ├── metrics/        # EWMA engine
│   └── scoring/        # Scoring engine
├── drivers/            # Kernel interfaces
│   └── ebpf/           # eBPF source & bridge
├── internal/           # Infrastructure
│   ├── container/      # Docker resolver
│   └── storage/        # SQLite persistence
├── web/                # Frontend assets
│   └── index.html      # Dashboard
├── scripts/            # Utils & Attacks
├── tests/              # unit/ & integration/
├── data/               # Persistent storage
└── ARCHITECTURE.md
```

---

*Generated: April 2026, updated May 2026*
*Version: 0.1.0*