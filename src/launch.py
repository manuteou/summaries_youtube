import os
import sys
import time
import subprocess
from pyngrok import ngrok

def main():
    # 1. Start ngrok tunnel
    # Determine port (default 8501)
    port = 8501
    
    print("🚀 Starting ngrok tunnel...")
    
    # Check for auth token in env or ask user to set it if it fails
    # Note: ngrok might require auth token for http tunnels now.
    
    try:
        public_url = ngrok.connect(port).public_url
        print(f"✅ Tunnel Established!")
        print(f"🌍 Public URL: {public_url}")
        print(f"🔑 (Share this URL to access your app from anywhere)")
    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        print("💡 Tip: run 'python src/set_ngrok_token.py <YOUR_TOKEN>' to fix authentication.")
        sys.exit(1)

    # 2. Start Streamlit
    print("\n🚀 Starting Streamlit App...")
    
    # Run streamlit as a subprocess
    # We assume 'src/app.py' is relative to current working directory or script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.address", "0.0.0.0"]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        ngrok.kill()

if __name__ == "__main__":
    main()
