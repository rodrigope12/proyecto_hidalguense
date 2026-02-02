import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    print("❌ Error: GOOGLE_MAPS_API_KEY not found in environment.")
    exit(1)

print(f"🔑 Testing API Key: {API_KEY[:5]}...{API_KEY[-4:]}")

url = "https://places.googleapis.com/v1/places:searchText"

headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "places.displayName"
}

payload = {
    "textQuery": "Mercado",
    "maxResultCount": 1
}

print(f"\n📡 Sending request to: {url}")
try:
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"Start Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESS! Places API (New) is working.")
        print(json.dumps(response.json(), indent=2))
    else:
        print("❌ FAILURE!")
        print(f"Status: {response.status_code}")
        print("Response Body:")
        print(response.text)
        print("\nPossible Causes:")
        print("1. 'Places API (New)' is not enabled in Google Cloud Console.")
        print("2. The API Key has 'Application Restrictions' (IP/Referrer) blocking this script.")
        print("3. The API Key has 'API Restrictions' and 'Places API (New)' is not in the list.")

except Exception as e:
    print(f"💥 Exception: {e}")
