import sys
import os
from dotenv import load_dotenv
from app.integrations.google_sheets import GoogleSheetsClient

# Usage: python3 update_url.py "https://new-url.trycloudflare.com"

if len(sys.argv) < 2:
    print("Error: No URL provided.")
    sys.exit(1)

new_url = sys.argv[1]

load_dotenv()
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials/service_account.json')

if not SPREADSHEET_ID:
    print("Error: SPREADSHEET_ID not set.")
    sys.exit(1)

try:
    client = GoogleSheetsClient(GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID)
    client.connect()
    
    # Update SYSTEM_CONFIG sheet
    # We assume it exists (created by previous step or manual)
    # If not, let's create it on the fly to be safe
    try:
        ws = client._spreadsheet.worksheet('SYSTEM_CONFIG')
    except:
        ws = client._spreadsheet.add_worksheet(title='SYSTEM_CONFIG', rows=10, cols=2)
        ws.update('A1', 'CURRENT_API_URL')

    # Ensure A1 has the key (Fix for empty A1 causing APK parse failure)
    ws.update_acell('A1', 'CURRENT_API_URL')

    # Update Cell B1 with the new URL
    # Use update_acell for single cell update to avoid argument mismatch errors
    ws.update_acell('B1', new_url)
    print(f"SUCCESS: Updated Google Sheet with new URL: {new_url}")

except Exception as e:
    print(f"ERROR updating Google Sheet: {e}")
    sys.exit(1)
