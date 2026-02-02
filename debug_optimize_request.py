import requests
import json
import sys

# Detect today's date
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")

# URL (Local)
url = "http://localhost:8000/api/optimize-route"

# Payload (Mocking what the phone sends)
payload = {
    "fecha_ruta": today,
    "origin_lat": 20.3765, # Mock location
    "origin_lng": -99.6644,
    "test_mode": False 
}

print(f"🔵 Sending POST to {url}")
print(f"🔵 Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=60) # 60s timeout
    print(f"🟢 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("🟢 Optimization Result:")
        print(json.dumps(data, indent=2))
        
        if data.get("success"):
            route = data.get("optimized_route", [])
            print(f"✅ Route received with {len(route)} stops.")
            for i, order in enumerate(route):
                print(f"  {i+1}. {order.get('Nombre_Negocio')} ({order.get('Estatus')})")
        else:
            print("⚠️ Success=False in response")
            print(data.get("message"))
    else:
        print(f"🔴 Error: {response.text}")

except requests.exceptions.Timeout:
    print("🔴 Request Timed Out (Backend took too long)")
except Exception as e:
    print(f"🔴 Connection Error: {e}")
