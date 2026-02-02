
# ============ SPECIAL PRICES INJECTION ============
from pydantic import BaseModel

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
    except Exception as e:
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
