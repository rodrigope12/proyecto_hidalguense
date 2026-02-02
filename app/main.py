"""
Sistema de Logística "Última Milla"
Backend API con FastAPI

Optimización VRP con constraint de seguridad (Huichapan)
Integración con Google Sheets para AppSheet
"""
import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from app.models.schemas import (
    Client, Order, SpecialPrice,
    CreateClientRequest, CreateOrderRequest,
    OptimizeRouteRequest, OptimizeRouteResponse
)

from pydantic import BaseModel

from app.integrations.google_sheets import GoogleSheetsClient
from app.integrations.distance_matrix import DistanceMatrixClient, calculate_haversine_matrix
from app.integrations.pdf_generator import generate_receipt_pdf, generate_whatsapp_link
from app.optimization.vrp_solver import VRPSolver, DeliveryNode, build_distance_matrix_for_solver
from app.integrations.places_client import PlacesClient # NEW
import difflib # For fuzzy matching

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")

# Security waypoint (Huichapan)
# Security waypoint (Huichapan)
HUICHAPAN_LAT = float(os.getenv("HUICHAPAN_LAT", "20.3743125")) # Updated to 98FQ+P3
HUICHAPAN_LNG = float(os.getenv("HUICHAPAN_LNG", "-99.6623125"))

# Warehouse/Depot
WAREHOUSE_LAT = float(os.getenv("WAREHOUSE_LAT", "19.4326"))
WAREHOUSE_LNG = float(os.getenv("WAREHOUSE_LNG", "-99.1332"))
WAREHOUSE_NAME = os.getenv("WAREHOUSE_NAME", "Almacén Principal")

# Global clients
sheets_client: Optional[GoogleSheetsClient] = None
distance_client: Optional[DistanceMatrixClient] = None
places_client: Optional[PlacesClient] = None # NEW


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize connections on startup"""
    global sheets_client, distance_client, places_client, places_client
    
    # Initialize Google Sheets client
    print(f"DEBUG: SPREADSHEET_ID loaded: '{SPREADSHEET_ID}'")
    
    if SPREADSHEET_ID and "TU_SPREADSHEET_ID" not in SPREADSHEET_ID:
        try:
            sheets_client = GoogleSheetsClient(GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID)
            sheets_client.connect()
            print("✓ Google Sheets conectado")
        except Exception as e:
            print(f"⚠ Error conectando a Google Sheets: {e}")
            import traceback
            traceback.print_exc()
            sheets_client = None # Fallback to demo mode
    else:
        print("⚠ SPREADSHEET_ID no válido o es placeholder")
    
    # Initialize Distance Matrix client
    if GOOGLE_MAPS_API_KEY:
        distance_client = DistanceMatrixClient(GOOGLE_MAPS_API_KEY)
        places_client = PlacesClient(GOOGLE_MAPS_API_KEY) # NEW
        print("✓ Distance Matrix y Places API configurados")
    
    yield
    
    # Cleanup
    print("Cerrando conexiones...")


# Create FastAPI app
app = FastAPI(
    title="Sistema Última Milla",
    description="API de optimización de rutas para distribuidora de lácteos",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# ============ HEALTH CHECK ============

@app.get("/")
async def root():
    """Serve the frontend"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Sistema Última Milla API", "status": "running"}


@app.get("/sw.js")
async def service_worker():
    """Serve the service worker from root to allow root scope"""
    sw_path = os.path.join(frontend_path, "sw.js")
    return FileResponse(sw_path, media_type="application/javascript")


@app.get("/manifest.json")
async def manifest():
    """Serve manifest from root"""
    manifest_path = os.path.join(frontend_path, "manifest.json")
    return FileResponse(manifest_path, media_type="application/json")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "sheets_connected": sheets_client is not None,
        "distance_api_ready": distance_client is not None,
        "timestamp": datetime.now().isoformat()
    }


# ============ CLIENTS ============

@app.get("/api/clients")
async def get_clients():
    """Get all clients"""
    if not sheets_client:
        # Return demo data if not connected
        return {
            "clients": [
                {
                    "ID_Cliente": "CLI-DEMO001",
                    "Nombre_Negocio": "Cremería La Esperanza",
                    "Telefono": "5551234567",
                    "Latitud": 20.1234,
                    "Longitud": -99.4567,
                    "Zona": "Centro"
                }
            ],
            "demo_mode": True
        }
    
    try:
        clients = sheets_client.get_all_clients()
        return {"clients": clients, "demo_mode": False}
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in get_clients: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clients")
async def create_client(request: CreateClientRequest):
    """Create a new client with optional special price"""
    if not sheets_client:
        # Fallback for Demo/Offline mode
        print(f"⚠️ [DEMO MODE] Cliente recibido offline: {request}")
        return {
            "success": True,
            "client_id": f"DEMO-CLI-{int(datetime.now().timestamp())}",
            "message": f"Cliente '{request.nombre_negocio}' guardado (Modo Demo)"
        }
    
    try:
        print(f"DEBUG: Received Client Payload: {request.dict()}")
        # Create Client
        client_id = sheets_client.create_client({
            "nombre_negocio": request.nombre_negocio,
            "telefono": request.telefono,
            "latitud": request.latitud,
            "longitud": request.longitud,
            "zona": request.zona,
            "direccion": request.direccion,
            "telefono_extra": request.telefono_extra,
            "ruta_asignada": request.ruta_asignada,
            "producto": request.producto
        })
        
        # Create special price if provided
        if request.producto and request.precio_pactado:
            sheets_client.create_special_price(
                client_id, 
                request.producto, 
                request.precio_pactado
            )
        
        return {
            "success": True,
            "client_id": client_id,
            "message": f"Cliente '{request.nombre_negocio}' creado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/clients/{client_id}")
async def update_client(client_id: str, request: CreateClientRequest):
    """Update an existing client"""
    if not sheets_client:
        return {"success": True, "message": "Demo Mode: Client Updated"}
        
    try:
        success = sheets_client.update_client(client_id, {
            "nombre_negocio": request.nombre_negocio,
            "telefono": request.telefono,
            "latitud": request.latitud,
            "longitud": request.longitud,
            "zona": request.zona,
            "direccion": request.direccion,
            "telefono_extra": request.telefono_extra,
            "ruta_asignada": request.ruta_asignada,
            "producto": request.producto
        })
        
        if not success:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
        return {"success": True, "message": "Cliente actualizado"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@app.delete("/api/clients/{client_id}")
async def delete_client(client_id: str):
    """Delete a client"""
    if not sheets_client:
        # Check if it's a demo client
        if client_id == "CLI-DEMO001":
             return {"success": True, "message": "Demo Mode: Client Deleted"}
        # If it's a random offline client that somehow got here?
        return {"success": True, "message": "Demo Mode: Sync Deleted"}

    try:
        success = sheets_client.delete_client(client_id)
        if not success:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        return {"success": True, "message": "Cliente eliminado correctamente"}
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============ ORDERS ============

@app.get("/api/orders/{fecha_ruta}")
async def get_orders_by_date(fecha_ruta: str, status: Optional[str] = None):
    """Get orders for a specific date"""
    if not sheets_client:
        # Demo data
        return {
            "orders": [
                {
                    "ID_Pedido": "PED-DEMO001",
                    "Fecha_Ruta": fecha_ruta,
                    "ID_Cliente": "CLI-DEMO001",
                    "Nombre_Negocio": "Cremería La Esperanza",
                    "Latitud": 20.1234,
                    "Longitud": -99.4567,
                    "Estatus": "Confirmado",
                    "Producto": "Queso Oaxaca",
                    "Kg_Solicitados": 5.0
                }
            ],
            "demo_mode": True
        }
    
    try:
        orders = sheets_client.get_orders_by_date(fecha_ruta, status)
        # Enrich with client data
        clients = {c.get("ID_Cliente"): c for c in sheets_client.get_all_clients() if c.get("ID_Cliente")}
        for order in orders:
            client = clients.get(order.get("ID_Cliente"))
            if client:
                order["Nombre_Negocio"] = client.get("Nombre_Negocio")
                order["Latitud"] = client.get("Latitud")
                order["Longitud"] = client.get("Longitud")
                order["Telefono"] = client.get("Telefono")
                order["Direccion"] = client.get("Direccion")
                # Ensure it's an integer to avoid JS concatenation bugs (e.g. "1" + 1 = "11")
                try:
                    order["Contador_Ventas"] = int(client.get("Contador_Ventas") or 0)
                except:
                    order["Contador_Ventas"] = 0
        
        return {"orders": orders, "demo_mode": False}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orders")
async def create_order(request: CreateOrderRequest):
    """Create a new order (Preventa)"""
    if not sheets_client:
        # Fallback for Demo/Offline mode
        print(f"⚠️ [DEMO MODE] Pedido recibido offline: {request}")
        return {
            "success": True,
            "order_id": f"DEMO-PED-{int(datetime.now().timestamp())}",
            "message": "Pedido guardado (Modo Demo/Offline)"
        }
    
    try:
        order_id = sheets_client.create_order({
            "id_cliente": request.id_cliente,
            "fecha_ruta": request.fecha_ruta,
            "producto": request.producto,
            "kg_solicitados": request.kg_solicitados
        })
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "Pedido creado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@app.delete("/api/orders/{order_id}")
async def delete_order(order_id: str):
    """Delete an order"""
    if not sheets_client:
        return {"success": True, "message": "Demo Mode: Order Deleted"}
    
    try:
        success = sheets_client.delete_order(order_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
    return {"success": True, "message": "Pedido eliminado"}

@app.post("/api/orders/{order_id}/complete")
async def complete_delivery(order_id: str, kg_reales: float, background_tasks: BackgroundTasks):
    """Mark an order as delivered"""
    if not sheets_client:
        raise HTTPException(status_code=503, detail="Google Sheets no conectado")
    
    try:
        success = sheets_client.complete_delivery(order_id, kg_reales)
        
        if not success:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        # TODO: Generate PDF and upload to Drive in background
        # background_tasks.add_task(generate_and_upload_receipt, order_id)
        
        return {
            "success": True,
            "message": f"Entrega completada: {kg_reales} kg"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in complete_delivery: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============ MARKET DETECTION ============
class CheckMarketRequest(BaseModel):
    lat: float
    lng: float

@app.post("/api/check-market")
async def check_market(request: CheckMarketRequest):
    """Check if location is inside a market"""
    if not places_client:
        return {"market_name": None}
    
    market_name = places_client.detect_market(request.lat, request.lng)
    return {"market_name": market_name}


# ============ PROSPECTING (Lead Gen) ============
class SearchProspectsRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    region_query: Optional[str] = None # "San Juan del Rio, Qro"
    radius: Optional[int] = 5000

@app.post("/api/prospects/search")
async def search_prospects(request: SearchProspectsRequest):
    """
    Search for prospects (cremerías) nearby or in a specific region.
    Groups results by name to handle chains (e.g. 5 'OXXO's).
    """
    if not places_client:
        return {"success": False, "message": "Places API no configurada"}
    
    lat, lng = request.lat, request.lng
    print(f"DEBUG: Received Prospect Search Request: Lat={lat}, Lng={lng}, Radius={request.radius}, Region={request.region_query}")
    
    # Geocode region if provided
    if request.region_query:
        location = places_client.geocode_region(request.region_query)
        if location:
            lat, lng = location['lat'], location['lng']
        else:
            return {"success": False, "message": f"No se encontró la región: {request.region_query}"}
            
    if not lat or not lng:
        return {"success": False, "message": "Se requiere ubicación (lat/lng o región)"}
        
    # Search nearby
    # Search nearby with multiple keywords for better coverage
    # Updated per user request: Avoid generic "Abarrotes", focus on "Queseria/Cremeria"
    keywords = ["Cremería", "Quesería", "Lácteos", "Abarrotes y Cremería"]
    raw_results = []
    seen_ids = set()
    
    try:
        for kw in keywords:
            print(f"DEBUG: Searching for keyword: {kw}")
            results = places_client.search_nearby_places(lat, lng, request.radius, keyword=kw)
            
            for place in results:
                pid = place.get("place_id")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    raw_results.append(place)
                    
        print(f"DEBUG: Total unique places found: {len(raw_results)}")
        
    except Exception as e:
        print(f"Error en search_nearby_places: {e}")
        return {"success": False, "message": f"Error buscando prospectos: {str(e)}"}
    
    # Smart Grouping Logic
    grouped_results = {}
    singles = []
    
    for place in raw_results:
        original_name = place['name']
        # Normalize name for explicit groups (Chains)
        normalized_name = original_name
        
        lower_name = original_name.lower()
        if "san juan" in lower_name and "cremer" in lower_name: 
            normalized_name = "Cremería San Juan (Cadena)"
        elif "forastero" in lower_name:
            normalized_name = "Cremería El Forastero (Cadena)"
            
        # Try to find an existing group matching this normalized name
        found_group = False
        
        # 1. Check Exact Match (for normalized chains)
        if normalized_name in grouped_results:
             grouped_results[normalized_name].append(place)
             found_group = True
        else:
             # 2. Check Fuzzy Match (only if not a normalized chain)
             # If it's a normalized chain, we start a NEW group with that name if not found above.
             if normalized_name == original_name: 
                 for group_name in grouped_results.keys():
                    # If similarity > 0.95 (difflib) - STRICTER grouping for others
                    ratio = difflib.SequenceMatcher(None, group_name.lower(), normalized_name.lower()).ratio()
                    if ratio > 0.95:
                        grouped_results[group_name].append(place)
                        found_group = True
                        break
        
        if not found_group:
            grouped_results[normalized_name] = [place]
            
    # Format output
    final_output = []
    for name, group in grouped_results.items():
        if len(group) > 1:
            # It's a chain/group
            # Pick center-most or first as representative
            rep = group[0]
            final_output.append({
                "type": "group",
                "name": f"{name} ({len(group)} sucursales)",
                "count": len(group),
                "representative": rep,
                "places": group
            })
        else:
            # Single
            final_output.append({
                "type": "single",
                "place": group[0]
            })
            
    return {
        "success": True,
        "center": {"lat": lat, "lng": lng},
        "results": final_output
    }

class AddProspectRequest(BaseModel):
    nombre_negocio: str
    direccion: str
    latitud: float
    longitud: float
    interes_producto: str = "Queso Oaxaca"
    precio_oferta: float = 160.0
    fecha_ruta: Optional[str] = None

@app.post("/api/prospects")
async def add_prospect(request: AddProspectRequest):
    """Save a prospect to Google Sheets"""
    if not sheets_client:
        return {"success": True, "message": "Modo Demo: Prospecto Guardado"}
        
    try:
        prospect_id = sheets_client.create_prospect(request.model_dump())
        return {
            "success": True, 
            "prospect_id": prospect_id,
            "message": "Prospecto agregado a la lista"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prospects")
async def get_prospects(date: Optional[str] = Query(None)):
    """Get prospects for a specific date (or all pending if no date)"""
    if not sheets_client:
        return {"success": True, "results": []}
        
    try:
        # Re-use the existing logic in sheets_client
        prospects = sheets_client.get_pending_prospects(target_date=date)
        return {"success": True, "results": prospects}
    except Exception as e:
        print(f"Error getting prospects: {e}")
        return {"success": False, "message": str(e), "results": []}

@app.delete("/api/prospects/{prospect_id}")
async def delete_prospect(prospect_id: str):
    """Delete a prospect (or mark as cancelled?) For now assume delete row."""
    if not sheets_client:
        return {"success": True, "message": "Demo: Prospecto eliminado"}
        
    try:
        success = sheets_client.delete_prospect(prospect_id)
        return {"success": success, "message": "Prospecto eliminado"}
    except Exception as e:
        print(f"Error deleting prospect: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prospects/{prospect_id}/visit")
async def visit_prospect(prospect_id: str):
    """Mark a prospect as visited (Status = 'Entregado' or similar)."""
    if not sheets_client:
        return {"success": True, "message": "Demo: Prospecto visitado"}
    
    try:
        success = sheets_client.mark_prospect_visited(prospect_id)
        return {"success": success, "message": "Visita registrada"}
    except Exception as e:
        print(f"Error visiting prospect: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ ROUTE OPTIMIZATION ============

@app.post("/api/optimize-route")
async def optimize_route(request: OptimizeRouteRequest):
    """
    Optimize delivery route for a given date.
    
    HARD CONSTRAINT: Route must pass through Huichapan first (security).
    """
    print(f"DEBUG: Processing Optimize Request for {request.fecha_ruta}")
    # Use demo data if not connected or in test mode
    use_demo = request.test_mode or not sheets_client
    
    if use_demo:
        # Demo delivery locations
        deliveries = [
            {"id": "PED-001", "name": "Cremería La Esperanza", "lat": 20.4567, "lng": -99.8765},
            {"id": "PED-002", "name": "Tienda Don José", "lat": 20.5432, "lng": -99.7654},
            {"id": "PED-003", "name": "Abarrotes María", "lat": 20.3456, "lng": -99.6543},
            {"id": "PED-004", "name": "Mini Super El Sol", "lat": 20.2345, "lng": -99.5432},
            {"id": "PED-005", "name": "Cremería Los Ángeles", "lat": 20.6789, "lng": -99.4321},
        ]
    else:
        try:
            # 1. Get confirmed orders
            orders = sheets_client.get_orders_for_optimization(request.fecha_ruta)
            
            # 2. Get active prospects
            # 2. Get active prospects (Global + Assigned to this Date)
            prospects = sheets_client.get_pending_prospects(target_date=request.fecha_ruta)
            
            deliveries = []
            
            # Process Orders
            for o in orders:
                try:
                    lat_raw = o.get("Latitud")
                    lng_raw = o.get("Longitud")
                    if lat_raw and lng_raw:
                        deliveries.append({
                            "id": o.get("ID_Pedido"),
                            "name": o.get("Nombre_Negocio", "Cliente"),
                            "lat": float(lat_raw),
                            "lng": float(lng_raw),
                            "type": "order", # Yellow
                            "zona": o.get("Zona", "")
                        })
                    else:
                        print(f"DEBUG: Skipping Order {o.get('ID_Pedido')} - Missing Coords")
                except ValueError:
                    print(f"DEBUG: Skipping Order {o.get('ID_Pedido')} - Invalid Coords: {lat_raw}, {lng_raw}")

            print(f"DEBUG: Found {len(orders)} total orders. Filtered down to {len([d for d in deliveries if d['type'] == 'order'])} valid locations.")
                    
            # Process Prospects
            for p in prospects:
                try:
                    lat_raw = p.get("Latitud")
                    lng_raw = p.get("Longitud")
                    if lat_raw and lng_raw:
                        deliveries.append({
                            "id": p.get("ID_Prospecto"),
                            "name": f"[PROSPECTO] {p.get('Nombre_Negocio')}",
                            "lat": float(lat_raw),
                            "lng": float(lng_raw),
                            "type": "prospect", # Blue
                            "zona": "" # Prospects don't have zone yet
                        })
                    else:
                        print(f"DEBUG: Skipping Prospect {p.get('ID_Prospecto')} - Missing Coords")
                except ValueError:
                     print(f"DEBUG: Skipping Prospect {p.get('ID_Prospecto')} - Invalid Coords: {lat_raw}, {lng_raw}")

            print(f"DEBUG: Added {len([d for d in deliveries if d['type'] == 'prospect'])} prospects to optimization nodes.")

        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error processing locations: {e}")
    
    if not deliveries:
        return OptimizeRouteResponse(
            success=False,
            message="No hay pedidos confirmados para optimizar",
            optimized_order=[],
            total_distance_km=0,
            total_time_minutes=0
        )

    # --- GROUPING LOGIC (MARKET ZONES) ---
    all_deliveries_flat = deliveries
    grouped_deliveries = {} 
    singles = []
    
    for d in all_deliveries_flat:
        zona = d.get("zona", "").strip()
        if zona:
             zone_key = zona.lower()
             if zone_key not in grouped_deliveries:
                 grouped_deliveries[zone_key] = []
             grouped_deliveries[zone_key].append(d)
        else:
             singles.append(d)
    
    # Create Nodes for Solver (Proxy Nodes)
    solver_nodes_map = {} # { 'NODE_ID': [original_delivery_dict] }
    final_nodes_for_solver = []
    
    # Add Singles
    for d in singles:
        solver_nodes_map[d["id"]] = [d]
        final_nodes_for_solver.append(d)
        
    # Add Groups
    for zone_key, items in grouped_deliveries.items():
        if len(items) == 1:
             d = items[0]
             solver_nodes_map[d["id"]] = [d]
             final_nodes_for_solver.append(d)
        else:
             # Calculate Centroid
             avg_lat = sum(d["lat"] for d in items) / len(items)
             avg_lng = sum(d["lng"] for d in items) / len(items)
             proxy_name = f"Zona: {items[0].get('zona')}"
             proxy_id = f"GROUP_{zone_key}"
             
             proxy_node = {
                 "id": proxy_id,
                 "name": proxy_name,
                 "lat": avg_lat,
                 "lng": avg_lng,
                 "type": "group",
                 "zona": items[0].get("zona")
             }
             
             solver_nodes_map[proxy_id] = items
             final_nodes_for_solver.append(proxy_node)
             print(f"DEBUG: Created Proxy Node {proxy_id} ({proxy_name}) with {len(items)} items")
    
    # Use optimized list for solver
    deliveries_for_solver = final_nodes_for_solver
    
    # Build delivery nodes
    delivery_nodes = [
        DeliveryNode(
            id=d["id"],
            name=d["name"],
            lat=d["lat"],
            lng=d["lng"]
        )
        for d in deliveries_for_solver
    ]
    
    # Determine Depot Location
    depot_lat, depot_lng = WAREHOUSE_LAT, WAREHOUSE_LNG
    depot_name = WAREHOUSE_NAME
    
    if request.origin_lat and request.origin_lng:
        try:
            depot_lat = float(request.origin_lat)
            depot_lng = float(request.origin_lng)
            depot_name = "Ubicación Actual (GPS)"
            print(f"DEBUG: Using Dynamic Origin: {depot_lat}, {depot_lng}")
        except ValueError:
            print("DEBUG: Invalid origin coordinates, using default Warehouse.")

    # Build locations list for distance matrix (using Solver Nodes)
    locations = [
        (depot_lat, depot_lng),  # Depot
        (HUICHAPAN_LAT, HUICHAPAN_LNG),  # Security waypoint
    ]
    locations.extend([(d["lat"], d["lng"]) for d in deliveries_for_solver])

    
    print(f"DEBUG: Distance Matrix Locations count: {len(locations)}")
    # Get distance matrix
    if distance_client and not use_demo:
        try:
            print("DEBUG: Requesting Distance Matrix from API...")
            matrix_result = distance_client.get_full_matrix(locations)
            distance_matrix = matrix_result["distances"]
            print(f"DEBUG: Distance Matrix API success. Size: {len(distance_matrix)}x{len(distance_matrix[0]) if distance_matrix else 0}")
        except Exception as e:
            print(f"DEBUG: Distance Matrix API error, falling back to Haversine: {e}")
            traceback.print_exc()
            distance_matrix = calculate_haversine_matrix(locations)
    else:
        print("DEBUG: Using Haversine Matrix (Demo/No API)")
        distance_matrix = calculate_haversine_matrix(locations)
    
    # Initialize solver
    solver = VRPSolver(
        depot_location=(depot_lat, depot_lng),
        depot_name=depot_name,
        security_waypoint=(HUICHAPAN_LAT, HUICHAPAN_LNG),
        security_waypoint_name="Huichapan (Waypoint Seguridad)"
    )
    
    
    # Solve
    print(f"DEBUG: Calling VRPSolver.solve with {len(delivery_nodes)} delivery nodes")
    print(f"DEBUG: Is distance_matrix valid? {bool(distance_matrix)}")
    if distance_matrix:
        print(f"DEBUG: Matrix Row Count: {len(distance_matrix)}")

    result = solver.solve(delivery_nodes, distance_matrix)
    print(f"DEBUG: Solver FINAL Result: Success={result.success}, Message={result.message}, Orders={len(result.ordered_nodes)}")
    
    if not result.success:
        return OptimizeRouteResponse(
            success=False,
            message=result.message,
            optimized_order=[],
            total_distance_km=0,
            total_time_minutes=0
        )
        
    # --- EXPANSION LOGIC ---
    # Expand Proxy Nodes back to original items
    ordered_nodes_expanded = []
    
    for node in result.ordered_nodes:
        if node.is_depot or node.is_security_waypoint:
            ordered_nodes_expanded.append(node)
            continue
            
        real_items = solver_nodes_map.get(node.id)
        if real_items:
            for item in real_items:
                ordered_nodes_expanded.append(DeliveryNode(
                    id=item["id"],
                    name=item["name"],
                    lat=item["lat"],
                    lng=item["lng"]
                ))
        else:
            # Should not happen
            ordered_nodes_expanded.append(node)
            
    # Replace result with expanded list
    result.ordered_nodes = ordered_nodes_expanded
    
    # Update Google Sheets with visit order
    if sheets_client and not use_demo:
        updates = []
        visit_order = 1
        for node in result.ordered_nodes:
            if not node.is_depot and not node.is_security_waypoint:
                updates.append({
                    "order_id": node.id,
                    "orden_visita": visit_order
                })
                visit_order += 1
        
        try:
            updated_count = sheets_client.batch_update_visit_orders(updates)
            print(f"Actualizados {updated_count} pedidos en Google Sheets")
        except Exception as e:
            print(f"Error actualizando Sheets: {e}")
    
    # Build response
    optimized_order = []
    visit_num = 0
    for node in result.ordered_nodes:
        node_data = {
            "id": node.id,
            "name": node.name,
            "lat": node.lat,
            "lng": node.lng,
            "is_depot": node.is_depot,
            "is_security_waypoint": node.is_security_waypoint,
            "type": next((d["type"] for d in all_deliveries_flat if d["id"] == node.id), "unknown") 
        }
        if not node.is_depot:
            visit_num += 1
            node_data["visit_order"] = visit_num
        optimized_order.append(node_data)
    
    return OptimizeRouteResponse(
        success=True,
        message=f"Ruta optimizada: {len(deliveries)} entregas + waypoint de seguridad",
        optimized_order=optimized_order,
        total_distance_km=round(result.total_distance_meters / 1000, 2),
        total_time_minutes=round(result.total_time_seconds / 60, 1)
    )


# ============ NAVIGATION ============

@app.get("/api/navigation/next")
async def get_next_delivery(fecha_ruta: str):
    """
    Get the next delivery in sequence (Uber-style navigation).
    Returns only the next pending delivery.
    """
    if not sheets_client:
        # Demo response
        return {
            "has_next": True,
            "delivery": {
                "ID_Pedido": "PED-DEMO001",
                "Nombre_Negocio": "Cremería La Esperanza",
                "Orden_Visita": 1,
                "Producto": "Queso Oaxaca",
                "Kg_Solicitados": 5.0,
                "Latitud": 20.1234,
                "Longitud": -99.4567,
                "nav_url": "https://www.google.com/maps/dir/?api=1&destination=20.1234,-99.4567"
            },
            "remaining": 4,
            "demo_mode": True
        }
    
    try:
        orders = sheets_client.get_orders_by_date(fecha_ruta, status="En Ruta")
        
        if not orders:
            return {"has_next": False, "delivery": None, "remaining": 0}
        
        # Sort by Orden_Visita and get the first one
        orders = [o for o in orders if o.get("Orden_Visita")]
        orders.sort(key=lambda x: int(x.get("Orden_Visita", 999)))
        
        if not orders:
            return {"has_next": False, "delivery": None, "remaining": 0}
        
        next_delivery = orders[0]
        
        # Enrich with client data
        client = sheets_client.get_client_by_id(next_delivery.get("ID_Cliente"))
        if client:
            next_delivery["Nombre_Negocio"] = client.get("Nombre_Negocio")
            next_delivery["Latitud"] = client.get("Latitud")
            next_delivery["Longitud"] = client.get("Longitud")
            next_delivery["Telefono"] = client.get("Telefono")
        
        # Add navigation URL
        lat = next_delivery.get("Latitud")
        lng = next_delivery.get("Longitud")
        if lat and lng:
            next_delivery["nav_url"] = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
        
        return {
            "has_next": True,
            "delivery": next_delivery,
            "remaining": len(orders) - 1
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============ WEEKLY SUMMARY ============

@app.get("/api/weekly-summary")
async def get_weekly_summary():
    """Get aggregated kg by product for purchasing decisions"""
    if not sheets_client:
        return {
            "summary": {
                "Queso Oaxaca": 45.5,
                "Queso Panela": 32.0,
                "Crema": 28.5
            },
            "demo_mode": True
        }
    
    try:
        summary = sheets_client.get_weekly_purchase_summary()
        return {"summary": summary, "demo_mode": False}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============ WHATSAPP LINK ============

@app.get("/api/whatsapp-link/{order_id}")
async def get_whatsapp_link(order_id: str):
    """Generate WhatsApp message link for an order"""
    if not sheets_client:
        return {
            "link": "https://wa.me/525551234567?text=Hola%20*Cremería%20La%20Esperanza*...",
            "demo_mode": True
        }
    
    try:
        # Get order data
        worksheet = sheets_client._spreadsheet.worksheet("PEDIDOS")
        cell = worksheet.find(order_id)
        if not cell:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
        row = worksheet.row_values(cell.row)
        order_data = {
            "ID_Pedido": row[0],
            "Fecha_Ruta": row[1],
            "ID_Cliente": row[2],
            "Producto": row[5],
            "Kg_Reales": row[7],
            "Total_Cobrar": row[9]
        }
        
        # Get client data
        client = sheets_client.get_client_by_id(order_data["ID_Cliente"])
        if client:
            order_data["Nombre_Negocio"] = client.get("Nombre_Negocio")
            phone = client.get("Telefono", "")
        else:
            phone = ""
        
        link = generate_whatsapp_link(phone, order_data)
        
        return {"link": link, "demo_mode": False}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============ SPECIAL PRICES ============

class CreateSpecialPriceRequest(BaseModel):
    id_cliente: str
    producto: str
    precio_pactado: float

@app.get("/api/clients/{client_id}/prices")
async def get_client_special_prices(client_id: str):
    """Get all special prices for this client"""
    if not sheets_client:
        return {"prices": {}, "demo_mode": True}
    
    try:
        prices = sheets_client.get_special_prices(client_id)
        # Simplify list: {"Queso Oaxaca": 140.0, ...}
        price_map = {}
        for p in prices:
            prod = p.get("Producto")
            try:
                val = float(p.get("Precio_Pactado", 0))
                if prod:
                    price_map[prod] = val
            except:
                pass
                
        return {"prices": price_map}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/special-prices")
async def create_special_price_endpoint(request: CreateSpecialPriceRequest):
    """Create a new special price rule"""
    if not sheets_client:
        return {"success": True, "message": "Demo Mode: Price Created"}
        
    try:
        rule_id = sheets_client.create_special_price(
            request.id_cliente,
            request.producto,
            request.precio_pactado
        )
        return {
            "success": True,
            "rule_id": rule_id,
            "message": f"Precio de ${request.precio_pactado} para '{request.producto}' guardado."
        }
    except Exception as e:
        print(f"Error creating price: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
