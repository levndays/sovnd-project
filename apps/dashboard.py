import streamlit as st
import pandas as pd
import plotly.express as px
import json
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import get_settings
from internal.storage.sqlite import StorageManager

settings = get_settings()
HEARTBEAT_FILE = Path(settings.heartbeat_path)

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="SovND | Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force Dark Mode CSS & Custom Styling
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .metric-card { 
        background-color: #1e293b; padding: 20px; border-radius: 8px; 
        border-left: 5px solid #3b82f6; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .alert-critical { 
        background-color: #450a0a; border-left: 5px solid #ef4444; 
        padding: 15px; border-radius: 5px; margin-bottom: 10px;
    }
    .stButton>button { width: 100%; font-weight: bold; }
    .attack-btn>button { background-color: #7f1d1d !important; color: white !important; border: 1px solid #ef4444 !important; }
    
    /* Attack flash animation */
    @keyframes flash-red {
        0% { box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0); }
        50% { box-shadow: inset 0 0 100px 50px rgba(239, 68, 68, 0.5); }
        100% { box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .attack-flash {
        animation: flash-red 1s ease-out;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- STATE & DATA -----------------
storage = StorageManager(db_path=settings.db_path)

if 'syscall_history' not in st.session_state:
    st.session_state.syscall_history =[]
if 'live_monitor' not in st.session_state:
    st.session_state.live_monitor = True
if 'attack_events' not in st.session_state:
    st.session_state.attack_events = []
if 'last_alert_count' not in st.session_state:
    st.session_state.last_alert_count = 0
if 'flash_screen' not in st.session_state:
    st.session_state.flash_screen = False

# Use PROJECT_ROOT which is correctly calculated above

def load_heartbeat():
    try:
        data = json.loads(HEARTBEAT_FILE.read_text())
        return data.get("events_per_sec", 0)
    except Exception:
        return 0

def launch_real_attack():
    """Executes the actual attacks directly from Python, no external scripts needed."""
    try:
        # 1. Trigger /etc/shadow read alert (Signature Match)
        subprocess.run(["cat", "/etc/shadow"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. Trigger Docker sock access alert (Signature Match)
        subprocess.run(["cat", "/var/run/docker.sock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 3. Trigger suspicious shell (Heuristic)
        subprocess.run(["bash", "-c", "echo 'stealth shell'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Mark attack time for graph highlighting
        st.session_state.attack_events.append(datetime.now())
        # Clean up old attack markers (older than 60 seconds)
        st.session_state.attack_events = [
            t for t in st.session_state.attack_events 
            if (datetime.now() - t).total_seconds() < 60
        ]
        
        return True
    except Exception as e:
        st.error(f"Failed to launch attack: {e}")
        return False

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
    st.title("SovND Control")
    st.markdown("---")
    
    st.session_state.live_monitor = st.toggle("🔴 Live Auto-Refresh", value=st.session_state.live_monitor)
    
    st.markdown("---")
    st.markdown("### ⚠️ Live Demo Actions")
    st.caption("These buttons execute REAL scripts on the host machine.")
    
    # Wrap button in custom class for red styling
    st.markdown('<div class="attack-btn">', unsafe_allow_html=True)
    if st.button("💥 LAUNCH REAL ATTACK", use_container_width=True):
        launch_real_attack()
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- MAIN DASHBOARD -----------------
st.title("🛡️ SovND Security Command Center")
st.caption("Live eBPF Kernel Telemetry & Threat Detection")

# Apply flash effect if new alerts
if st.session_state.flash_screen:
    st.markdown("""
        <div class="attack-flash" style="position:fixed; top:0; left:0; right:0; bottom:0; pointer-events:none; z-index:9999;"></div>
    """, unsafe_allow_html=True)
    st.session_state.flash_screen = False

# 1. Fetch live data
alerts_data = storage.get_recent_alerts(limit=50)
df_alerts = pd.DataFrame(alerts_data) if alerts_data else pd.DataFrame()
total_alerts = len(df_alerts)

# Trigger flash if new alerts appeared
if total_alerts > st.session_state.last_alert_count:
    st.session_state.flash_screen = True
st.session_state.last_alert_count = total_alerts

current_eps = load_heartbeat()
st.session_state.syscall_history.append({"time": datetime.now(), "events": current_eps})
if len(st.session_state.syscall_history) > 30: # Keep last 30 seconds
    st.session_state.syscall_history.pop(0)

# 2. Top KPIs
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#94a3b8; font-size:1rem;">Kernel Events / Sec</h3>
            <h1 style="margin:0; font-size:2.5rem;">{current_eps}</h1>
        </div>
    """, unsafe_allow_html=True)
with k2:
    alert_color = "#ef4444" if total_alerts > 0 else "#22c55e"
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: {alert_color};">
            <h3 style="margin:0; color:#94a3b8; font-size:1rem;">Total Critical Alerts</h3>
            <h1 style="margin:0; font-size:2.5rem; color:{alert_color};">{total_alerts}</h1>
        </div>
    """, unsafe_allow_html=True)
with k3:
    status = "Active & Enforcing" if st.session_state.live_monitor else "Paused"
    st.markdown(f"""
        <div class="metric-card" style="border-left-color: #10b981;">
            <h3 style="margin:0; color:#94a3b8; font-size:1rem;">eBPF Engine Status</h3>
            <h1 style="margin:0; font-size:1.8rem; padding-top:10px; color:#10b981;">{status}</h1>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 3. Main View: Chart on left, Alerts on right
col_chart, col_alerts = st.columns([2, 1])

with col_chart:
    st.markdown("### 📈 Live System Call Throughput")
    if len(st.session_state.syscall_history) > 1:
        df_history = pd.DataFrame(st.session_state.syscall_history)
        
        # Create the chart
        fig = px.area(df_history, x='time', y='events', 
                     color_discrete_sequence=['#3b82f6'],
                     template="plotly_dark")
        
        # Add red zones for attack periods (last 10 seconds after each attack)
        now = datetime.now()
        for attack_time in st.session_state.attack_events:
            time_diff = (now - attack_time).total_seconds()
            if time_diff < 10:
                # Convert datetime to timestamp for plotly
                attack_ts = attack_time.timestamp()
                end_ts = min(attack_ts + 5, now.timestamp())
                if end_ts > attack_ts:
                    fig.add_vrect(
                        x0=attack_ts, 
                        x1=end_ts,
                        fillcolor="rgba(239, 68, 68, 0.25)", 
                        opacity=0.25, 
                        line_width=0,
                        annotation_text="ATTACK", 
                        annotation_position="top left",
                        annotation_font_color="red"
                    )
        
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350,
                          xaxis_title="", yaxis_title="Events / Sec")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gathering kernel telemetry...")

with col_alerts:
    st.markdown("### 🚨 Live Threat Feed")
    if not df_alerts.empty:
        # Show top 4 most recent alerts
        for _, row in df_alerts.head(4).iterrows():
            reasons = ", ".join(row['reasons']) if isinstance(row['reasons'], list) else row['reasons']
            st.markdown(f"""
                <div class="alert-critical">
                    <div style="font-size: 0.8rem; color: #fca5a5;">{row['timestamp']}</div>
                    <strong style="font-size: 1.1rem;">PID {row['pid']} - {row.get('severity', 'CRITICAL').upper()}</strong><br>
                    <span style="font-size: 0.9rem;">{reasons}</span>
                </div>
            """, unsafe_allow_html=True)
        if len(df_alerts) > 4:
            st.caption(f"+ {len(df_alerts) - 4} older alerts hidden.")
    else:
        st.markdown("""
            <div style="padding:20px; text-align:center; color:#94a3b8; border: 1px dashed #334155; border-radius: 5px;">
                ✅ System is secure. No anomalous activity detected.
            </div>
        """, unsafe_allow_html=True)

# 4. Auto-refresh loop
if st.session_state.live_monitor:
    time.sleep(1.5)
    st.rerun()