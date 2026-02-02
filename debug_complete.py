import os
import sys
import traceback
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

load_dotenv()

from app.integrations.google_sheets import GoogleSheetsClient

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

print(f"DEBUG: Service Account: {GOOGLE_SERVICE_ACCOUNT_FILE}")
print(f"DEBUG: Spreadsheet ID: {SPREADSHEET_ID}")

if not SPREADSHEET_ID:
    print("Error: SPREADSHEET_ID not set")
    sys.exit(1)

try:
    print(f"Connecting to sheet...")
    client = GoogleSheetsClient(GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID)
    client.connect()
    
    ORDER_ID = "PED-5C49728A" 
    KG_REALES = 1.6
    
    print(f"Attempting complete_delivery for {ORDER_ID} with {KG_REALES}kg...")
    result = client.complete_delivery(ORDER_ID, KG_REALES)
    print(f"Result: {result}")

except Exception:
    traceback.print_exc()
