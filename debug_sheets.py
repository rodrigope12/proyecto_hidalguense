from app.integrations.google_sheets import GoogleSheetsClient
import os
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")

print(f"Connecting to Spreadsheet: {SPREADSHEET_ID}")
try:
    client = GoogleSheetsClient(CREDENTIALS_FILE, SPREADSHEET_ID)
    client.connect()
    
    ws = client._spreadsheet.worksheet("CLIENTES")
    headers = ws.row_values(1)
    print(f"HEADERS FOUND ({len(headers)}):")
    print(headers)
    
    # Check for duplicates
    if len(headers) != len(set(headers)):
        print("🚨 ERROR: DUPLICATE HEADERS DETECTED!")
        seen = set()
        dupes = [x for x in headers if x in seen or seen.add(x)]
        print(f"Duplicates: {dupes}")
        
    print("\nTrying get_all_records()...")
    records = ws.get_all_records()
    print(f"Successfully fetched {len(records)} records.")
    
except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
