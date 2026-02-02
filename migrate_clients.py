import sys
import os
import gspread
from dotenv import load_dotenv
from app.integrations.google_sheets import GoogleSheetsClient

# Usage: python3 migrate_clients.py

load_dotenv()
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials/service_account.json')

if not SPREADSHEET_ID:
    print("Error: SPREADSHEET_ID not set.")
    sys.exit(1)

try:
    client = GoogleSheetsClient(GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID)
    client.connect()
    
    print("Fetching all clients...")
    worksheet = client._spreadsheet.worksheet("CLIENTES")
    all_clients = client.get_all_clients()
    
    print(f"Found {len(all_clients)} clients. Starting migration to 'Ruta Queretana'...")
    
    # Batch update might be faster, but let's do safe row-by-row for now or batch column update
    # Column 11 (K) is Ruta_Asignada
    
    # Let's find the column index for "Ruta_Asignada" just to be safe
    headers = worksheet.row_values(1)
    try:
        col_idx = headers.index("Ruta_Asignada") + 1
    except ValueError:
        print("Error: Column 'Ruta_Asignada' not found.")
        sys.exit(1)
        
    # Prepare batch update
    # We want to update K2:K{len+1}
    cell_range = f"{gspread.utils.rowcol_to_a1(2, col_idx)}:{gspread.utils.rowcol_to_a1(len(all_clients) + 1, col_idx)}"
    
    # We can use update_cells if we had cell objects, or just update(range, values)
    # The values should be a list of lists: [["Ruta Queretana"], ["Ruta Queretana"], ...]
    new_values = [["Ruta Queretana"] for _ in range(len(all_clients))]
    
    import gspread.utils
    
    if not new_values:
        print("No clients to update.")
        sys.exit(0)
        
    range_name = f"{gspread.utils.rowcol_to_a1(2, col_idx)}:{gspread.utils.rowcol_to_a1(len(all_clients) + 1, col_idx)}"
    print(f"Updating range {range_name} with 'Ruta Queretana'...")
    
    worksheet.update(range_name=range_name, values=new_values)
    
    print("Migration complete! All clients are now on 'Ruta Queretana'.")

except Exception as e:
    print(f"ERROR during migration: {e}")
    sys.exit(1)
