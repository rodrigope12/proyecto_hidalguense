import os
import sys
import asyncio
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

load_dotenv()

from app.main import optimize_route, OptimizeRouteRequest, sheets_client, distance_client, lifespan
from app.integrations.google_sheets import GoogleSheetsClient
from app.integrations.distance_matrix import DistanceMatrixClient
from fastapi import FastAPI

# Mock App for lifespan
app = FastAPI()

async def run_debug():
    print("--- STARTING DEBUG OPTIMIZATION ---")
    
    # Manually init clients
    global sheets_client
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    
    print("Connecting to Sheets...")
    sheets_client = GoogleSheetsClient(GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID)
    sheets_client.connect()
    
    # Init Distance Client
    global distance_client
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    if GOOGLE_MAPS_API_KEY:
         distance_client = DistanceMatrixClient(GOOGLE_MAPS_API_KEY)
         print("Distance Client Initialized.")
    else:
         print("Using Haversine (No key).")

    # Inject into main module
    import app.main
    app.main.sheets_client = sheets_client
    app.main.distance_client = distance_client

    # Create Request
    # Use the date from the logs: 2026-01-24
    target_date = "2026-01-24"
    # Test with a distinct location (e.g., somewhere in Huichapan or Tula)
    # Using Tula de Allende coordinates approx: 20.0526, -99.3444
    req = OptimizeRouteRequest(
        fecha_ruta=target_date, 
        test_mode=False,
        origin_lat=20.0526,
        origin_lng=-99.3444
    )
    
    print(f"\n--- INSPECTING SHEET DATA for {target_date} ---")
    ws = sheets_client._spreadsheet.worksheet("PEDIDOS")
    records = sheets_client._get_all_records_safe(ws)
    print(f"Total Rows: {len(records)}")
    if len(records) > 0:
        # print(f"Sample Row: {records[0]}")
        print("Dates found in sheet:")
        dates = set(r.get("Fecha_Ruta") for r in records)
        print(dates)
        
        print(f"\nRows for {target_date}:")
        target_rows = [r for r in records if r.get("Fecha_Ruta") == target_date]
        for row in target_rows:
            print(f" - ID: {row.get('ID_Pedido')}, Status: '{row.get('Estatus')}'")
    
    print(f"\nCalling optimize_route for {req.fecha_ruta}...")
    try:
        response = await optimize_route(req)
        print("\n--- RESPONSE ---")
        print(f"Success: {response.success}")
        print(f"Message: {response.message}")
        print(f"Orders: {len(response.optimized_order)}")
        for o in response.optimized_order:
            print(f" - {o.Orden_Visita}. {o.Nombre_Negocio} ({o.Estatus})")
            
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_debug())
