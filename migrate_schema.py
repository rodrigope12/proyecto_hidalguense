from app.integrations.google_sheets import GoogleSheetsClient
import os
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")

def migrate():
    print(f"Starting Migration for Sheet: {SPREADSHEET_ID}")
    client = GoogleSheetsClient(CREDENTIALS_FILE, SPREADSHEET_ID)
    client.connect()
    
    # 1. CLIENTES MIGRATION
    ws_clients = client._spreadsheet.worksheet("CLIENTES")
    headers = ws_clients.row_values(1)
    print(f"Current Client Headers: {headers}")
    
    required_client_cols = ["Direccion", "Contador_Ventas"]
    
    # Check for empty duplicates first (the crash cause)
    if len(headers) != len(set(headers)):
        print("⚠️ Found duplicate/empty headers. Cleaning up...")
        # Trim sheet to actual data width
        real_width = len([h for h in headers if h.strip()])
        ws_clients.resize(rows=ws_clients.row_count, cols=real_width)
        print(f"Resized CLIENTES to {real_width} columns.")
        headers = ws_clients.row_values(1) # Refresh
        
    # Add missing columns
    new_headers = list(headers)
    added = False
    for req in required_client_cols:
        if req not in new_headers:
            new_headers.append(req)
            added = True
            
    if added:
        print(f"Adding new headers: {new_headers}")
        # Resize to fit new columns
        ws_clients.resize(rows=ws_clients.row_count, cols=len(new_headers))
        ws_clients.update_cell(1, len(new_headers)-1, "Direccion")
        ws_clients.update_cell(1, len(new_headers), "Contador_Ventas")
        print("✅ Added 'Direccion' and 'Contador_Ventas' to CLIENTES.")
    else:
        print("✓ CLIENTES schema is up to date.")

    # 2. PEDIDOS MIGRATION
    try:
        ws_pedidos = client._spreadsheet.worksheet("PEDIDOS")
        p_headers = ws_pedidos.row_values(1)
        print(f"Current Order Headers: {p_headers}")
        
        if "Folio_Nota" not in p_headers:
             print("Adding 'Folio_Nota' to PEDIDOS...")
             ws_pedidos.resize(rows=ws_pedidos.row_count, cols=len(p_headers)+1)
             ws_pedidos.update_cell(1, len(p_headers)+1, "Folio_Nota")
             print("✅ Added 'Folio_Nota' to PEDIDOS.")
        else:
            print("✓ PEDIDOS schema is up to date.")
            
    except Exception as e:
        print(f"Error migrating PEDIDOS: {e}")

    print("\nMigration Complete. Attempting validation...")
    try:
        recs = ws_clients.get_all_records()
        print(f"SUCCESS! Read {len(recs)} clients without error.")
    except Exception as e:
        print(f"❌ VALIDATION FAILED: {e}")

if __name__ == "__main__":
    migrate()
