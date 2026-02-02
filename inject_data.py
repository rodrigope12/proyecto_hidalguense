from app.integrations.google_sheets import GoogleSheetsClient
import os
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")

# Data to Inject
LOCATIONS = [
    {
        "Nombre_Negocio": "Parada Técnica (Copiloto)",
        "Latitud": 20.122825,
        "Longitud": -98.766781,
        "Direccion": "Pachuca (Zona San Javier / Salida a Actopan)",
        "Frecuencia_Visita": "Diario",
        "Dia_Preferido": "Lunes"
    },
    {
        "Nombre_Negocio": "Punto de Paso (Huichapan)",
        "Latitud": 20.376800,
        "Longitud": -99.662100,
        "Direccion": "Estaciones Ruta Huichapan (Libramiento)",
        "Frecuencia_Visita": "Diario",
        "Dia_Preferido": "Lunes"
    },
    {
        "Nombre_Negocio": "Venta 1: San Juan del Río",
        "Latitud": 20.388800,
        "Longitud": -100.001600,
        "Direccion": "Mercado Reforma (El principal del centro)",
        "Frecuencia_Visita": "Semanal",
        "Dia_Preferido": "Lunes"
    },
    {
        "Nombre_Negocio": "Venta 2: San Juan del Río",
        "Latitud": 20.386100,
        "Longitud": -99.992800,
        "Direccion": "Mercado Juárez (Famoso por el tianguis sabatino)",
        "Frecuencia_Visita": "Semanal",
        "Dia_Preferido": "Lunes"
    },
    {
        "Nombre_Negocio": "Venta 3: Querétaro Capital",
        "Latitud": 20.592700,
        "Longitud": -100.385800,
        "Direccion": "Mercado de La Cruz (Zona Garibaldi/Gorditas)",
        "Frecuencia_Visita": "Semanal",
        "Dia_Preferido": "Lunes"
    },
    {
        "Nombre_Negocio": "Venta 4: Querétaro Capital",
        "Latitud": 20.586900,
        "Longitud": -100.393400,
        "Direccion": "Mercado Escobedo (Materias primas y mayoreo medio)",
        "Frecuencia_Visita": "Semanal",
        "Dia_Preferido": "Lunes"
    },
    {
        "Nombre_Negocio": "Venta 5 / Remate: Querétaro Capital",
        "Latitud": 20.602200,
        "Longitud": -100.396100,
        "Direccion": "Mercado \"El Tepetate\" (Zona popular para acabar carga)",
        "Frecuencia_Visita": "Semanal",
        "Dia_Preferido": "Lunes"
    }
]

def inject():
    print(f"Connecting to Sheet: {SPREADSHEET_ID}")
    client = GoogleSheetsClient(CREDENTIALS_FILE, SPREADSHEET_ID)
    client.connect()
    
    ws = client._spreadsheet.worksheet("CLIENTES")
    existing_data = ws.get_all_records()
    
    # Calculate next ID
    next_id_num = 1
    if existing_data:
        try:
            # Extract numbers from IDs like 'CLI-005'
            ids = [int(r['ID_Cliente'].split('-')[1]) for r in existing_data if 'ID_Cliente' in r and '-' in str(r['ID_Cliente'])]
            if ids:
                next_id_num = max(ids) + 1
        except Exception as e:
            print(f"Warning parsing IDs: {e}, starting from {len(existing_data) + 1}")
            next_id_num = len(existing_data) + 1

    rows_to_add = []
    
    for loc in LOCATIONS:
        # Generate ID
        new_id = f"CLI-{str(next_id_num).zfill(3)}"
        next_id_num += 1
        
        # Build Row
        # Schema: ID_Cliente, Nombre_Negocio, Latitud, Longitud, Direccion, Telefono, Frecuencia_Visita, Dia_Preferido, Ultima_Visita, Promedio_Venta, Contador_Ventas
        row = [
            new_id,
            loc["Nombre_Negocio"],
            loc["Latitud"],
            loc["Longitud"],
            loc["Direccion"],
            "0000000000", # Telefono Dummy
            loc["Frecuencia_Visita"],
            loc["Dia_Preferido"],
            "", # Ultima_Visita
            0,  # Promedio_Venta
            0   # Contador_Ventas
        ]
        rows_to_add.append(row)
        print(f"Preparing: {new_id} - {loc['Nombre_Negocio']}")

    if rows_to_add:
        print(f"Appending {len(rows_to_add)} rows...")
        ws.append_rows(rows_to_add)
        print("✅ Success! Data injected.")
    else:
        print("No data to add.")

if __name__ == "__main__":
    inject()
