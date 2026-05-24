import subprocess
import time
import sys
import os

def start():
    if os.geteuid() != 0:
        print("❌ ERROR: The demo orchestrator must run as root (sudo).")
        sys.exit(1)

    real_user = os.environ.get('SUDO_USER')
    print("🛡️  SovND | Initializing SOC Demo...")
    
    # 1. Clean data for fresh start
    if os.path.exists("data/sovnd.db"):
        os.remove("data/sovnd.db")
    os.makedirs("data", exist_ok=True)
    os.chmod("data", 0o777)

    # 2. Start Dashboard Backend (User Port 8000)
    api_proc = subprocess.Popen([sys.executable, "-u", "-m", "uvicorn", "apps.server:app", "--host", "0.0.0.0", "--port", "8000"])
    
    # 3. Start eBPF Agent (Kernel Monitor)
    agent_proc = subprocess.Popen([sys.executable, "-u", "apps/agent.py"])

    time.sleep(2)
    print("\n🚀 ANALYTICS ENGINE READY: http://localhost:8000")
    
    # 4. Open browser as the regular user
    if real_user:
        os.system(f"sudo -u {real_user} xdg-open http://localhost:8000 > /dev/null 2>&1 &")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down SovND...")
        api_proc.terminate()
        agent_proc.terminate()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        start()
    else:
        print("Usage: sudo python3 apps/demo.py start")