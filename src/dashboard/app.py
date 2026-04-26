import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_agraph import agraph, Node, Edge, Config
import json
from datetime import datetime
import time

from src.storage.sqlite import StorageManager

# Page Configuration
st.set_page_config(
    page_title="SovND | Security Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern look
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Storage
storage = StorageManager()

def load_data():
    alerts = storage.get_recent_alerts(limit=100)
    return pd.DataFrame(alerts)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=80)
    st.title("SovND Control")
    st.markdown("---")
    
    threshold = st.slider("Anomaly Threshold (T)", 1.0, 50.0, 10.0)
    refresh_rate = st.selectbox("Refresh Rate", [5, 10, 30, 60], index=0)
    
    st.markdown("---")
    st.info("eBPF Monitor: **Active**")
    st.info("Kernel Version: **Linux 6.x**")

# Header
st.title("🛡️ SovND Security Dashboard")
st.caption("Real-time eBPF System Monitoring & Anomaly Detection")

# Main Tabs
tab_dash, tab_alerts, tab_graph = st.tabs(["📊 Dashboard", "🚨 Security Alerts", "🕸️ Provenance Graph"])

df_alerts = load_data()

with tab_dash:
    # Top Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Alerts", len(df_alerts))
    with m2:
        critical_count = len(df_alerts[df_alerts['severity'] == 'critical']) if not df_alerts.empty else 0
        st.metric("Critical Threats", critical_count, delta_color="inverse")
    with m3:
        st.metric("Monitored Containers", 5) # Placeholder
    with m4:
        st.metric("Kernel Events/sec", "1.2k") # Placeholder

    st.markdown("### Severity Distribution")
    if not df_alerts.empty:
        fig = px.pie(df_alerts, names='severity', color='severity',
                    color_discrete_map={'critical':'#ef4444', 'warning':'#f59e0b', 'info':'#3b82f6'},
                    hole=0.4)
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No alert data available yet.")

with tab_alerts:
    st.subheader("Recent Security Incidents")
    if not df_alerts.empty:
        # Clean the dataframe for display
        display_df = df_alerts.copy()
        display_df['reasons'] = display_df['reasons'].apply(lambda x: ", ".join(json.loads(x)) if x else "")
        st.dataframe(
            display_df[['timestamp', 'severity', 'pid', 'score', 'reasons']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No alerts detected in the current monitoring window.")

with tab_graph:
    st.subheader("Interactive Provenance Graph")
    st.caption("Visualize interactions between processes and system resources.")
    
    # Mock Graph for demonstration if no real data
    nodes = [
        Node(id="web-app", label="Web Server", size=25, color="#3b82f6"),
        Node(id="sh", label="sh", size=20, color="#ef4444"),
        Node(id="etc-shadow", label="/etc/shadow", size=15, color="#ef4444", shape="dot"),
        Node(id="etc-passwd", label="/etc/passwd", size=15, color="#10b981", shape="dot"),
    ]
    edges = [
        Edge(source="web-app", target="etc-passwd", label="read"),
        Edge(source="web-app", target="sh", label="exec"),
        Edge(source="sh", target="etc-shadow", label="open"),
    ]

    config = Config(width=1000, 
                    height=500, 
                    directed=True,
                    physics=True, 
                    hierarchical=False)

    return_value = agraph(nodes=nodes, 
                          edges=edges, 
                          config=config)

# Auto-refresh logic
if st.checkbox("Enable Real-time Refresh"):
    time.sleep(refresh_rate)
    st.rerun()
