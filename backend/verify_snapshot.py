import sys
import os
import time
import threading
import requests
import uvicorn

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.main import app
    from backend.config import TEST_PORT
    print("Successfully imported app")
except ImportError:
    try:
        from main import app
        from backend.config import TEST_PORT
        print("Successfully imported app (local)")
    except ImportError:
        print("Failed to import app")
        sys.exit(1)

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=TEST_PORT, log_level="critical")

def verify_snapshot():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    print("Waiting for server to start...")
    time.sleep(5)

    print(f"Testing GET http://127.0.0.1:{TEST_PORT}/api/market/snapshot...")
    try:
        response = requests.get(f"http://127.0.0.1:{TEST_PORT}/api/market/snapshot")
        
        if response.status_code == 200:
            print("✅ Status Code: 200 OK")
            data = response.json()
            instruments = data.get("instruments", {})
            print(f"✅ Received snapshot for {len(instruments)} instruments")
            
            if instruments:
                first = list(instruments.keys())[0]
                print(f"   Sample ({first}): {len(instruments[first].get('close', []))} candles")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    verify_snapshot()
