"""
Google Sheets integration for reading/writing logistics data
"""
import os
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import traceback


class GoogleSheetsClient:
    """Client for interacting with Google Sheets as database"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
    
    def connect(self) -> None:
        """Initialize connection to Google Sheets"""
        creds = Credentials.from_service_account_file(
            self.credentials_path, 
            scopes=self.SCOPES
        )
        self._client = gspread.authorize(creds)
        self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)
        self._initialize_schema()
    
    def ensure_connected(self) -> None:
        """Ensure we have an active connection"""
        if not self._spreadsheet:
            self.connect()

    def _initialize_schema(self) -> None:
        """Create required worksheets and headers if they don't exist, and update missing headers"""
        required_sheets = {
            "CLIENTES": [
                "ID_Cliente", "Nombre_Negocio", "Telefono", 
                "Latitud", "Longitud", "Zona", "Fecha_Creacion", 
                "Direccion", "Contador_Ventas", "Telefono_Extra", 
                "Ruta_Asignada", "Producto"
            ],
            "PEDIDOS": [
                "ID_Pedido", "Fecha_Ruta", "ID_Cliente", "Estatus",
                "Orden_Visita", "Producto", "Kg_Solicitados",
                "Kg_Reales", "Precio_Unitario", "Total_Cobrar", 
                "Timestamp_Entrega", "Folio_Nota"
            ],
            "PRECIOS_ESPECIALES": [
                "ID_Regla", "ID_Cliente", "Producto", "Precio_Pactado"
            ],
            "PROSPECTOS": [
                "ID_Prospecto", "Nombre_Negocio", "Direccion", 
                "Latitud", "Longitud", "Estatus", "Fecha_Registro", 
                "Interes_Producto", "Precio_Oferta", "Fecha_Ruta"
            ]
        }
        
        existing_sheets = {ws.title: ws for ws in self._spreadsheet.worksheets()}
        
        for sheet_name, required_headers in required_sheets.items():
            if sheet_name not in existing_sheets:
                # Create new sheet
                ws = self._spreadsheet.add_worksheet(sheet_name, rows=1000, cols=len(required_headers))
                ws.append_row(required_headers)
                print(f"✓ Creada hoja '{sheet_name}' con cabeceras.")
            else:
                # Update existing sheet headers
                ws = existing_sheets[sheet_name]
                current_headers = ws.row_values(1)
                
                # Find missing headers (append only to avoid breaking order)
                # This assumes we only ADD columns at the end
                missing_headers = [h for h in required_headers if h not in current_headers]
                
                if missing_headers:
                    print(f"⚠ Actualizando cabeceras en '{sheet_name}': {missing_headers}")
                    # Start appending from the next column
                    start_col = len(current_headers) + 1
                    
                    # Check if we need to resize
                    needed_cols = start_col + len(missing_headers) - 1
                    if needed_cols > ws.col_count:
                        print(f"📏 Redimensionando '{sheet_name}' de {ws.col_count} a {needed_cols} columnas...")
                        ws.resize(cols=needed_cols)

                    # Update cells
                    for i, header in enumerate(missing_headers):
                        ws.update_cell(1, start_col + i, header)
                        
                    print(f"✓ Cabeceras actualizadas en '{sheet_name}'")
    
    def _get_all_records_safe(self, worksheet) -> List[Dict[str, Any]]:
        """
        Safe alternative to get_all_records() that handles duplicate/empty headers
        by ignoring empty header columns and keeping the last value for duplicates.
        Returns values as strings (gspread default for get_all_values).
        """
        rows = worksheet.get_all_values()
        if not rows:
            return []
        
        headers = rows[0]
        records = []
        
        for row in rows[1:]:
            record = {}
            # effective_len = min(len(headers), len(row))
            # Zip allows pairing; if row is shorter, zip stops. 
            # If row is longer, zip stops at headers.
            # We treat strict pairing.
            
            for h, v in zip(headers, row):
                if h and str(h).strip(): # Only include if header is non-empty
                    record[h] = v
                    
            records.append(record)
            
        return records

    # ============ CLIENTES ============
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """Get all clients from CLIENTES sheet"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("CLIENTES")
        records = self._get_all_records_safe(worksheet)
        return records
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific client by ID"""
        clients = self.get_all_clients()
        for client in clients:
            if client.get("ID_Cliente") == client_id:
                return client
        return None
    
    def create_client(self, client_data: Dict[str, Any]) -> str:
        """Create a new client and return the ID"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("CLIENTES")
        
        # Generate ID
        client_id = f"CLI-{uuid.uuid4().hex[:8].upper()}"
        
        row = [
            client_id,
            client_data.get("nombre_negocio", ""),
            client_data.get("telefono", ""),
            client_data.get("latitud", 0),
            client_data.get("longitud", 0),
            client_data.get("zona", ""),
            datetime.now().strftime("%Y-%m-%d"),
            client_data.get("direccion", ""),
            0,  # Contador_Ventas starts at 0
            client_data.get("telefono_extra", ""),
            client_data.get("ruta_asignada", ""),
            client_data.get("producto", "")
        ]
        
        worksheet.append_row(row)
        return client_id
        return client_id
    
    def update_client(self, client_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing client's info"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("CLIENTES")
        
        cell = worksheet.find(client_id)
        if not cell:
            return False
            
        row = cell.row
        
        # Columns: ID(1), Nombre(2), Tel(3), Lat(4), Lng(5), Zona(6), Fecha(7), Direccion(8), Contador(9)
        if "nombre_negocio" in updates:
            worksheet.update_cell(row, 2, updates["nombre_negocio"])
        if "telefono" in updates:
            worksheet.update_cell(row, 3, updates["telefono"])
        if "latitud" in updates:
            worksheet.update_cell(row, 4, updates["latitud"])
        if "longitud" in updates:
            worksheet.update_cell(row, 5, updates["longitud"])
        if "zona" in updates:
            worksheet.update_cell(row, 6, updates["zona"])
        if "direccion" in updates:
            worksheet.update_cell(row, 8, updates["direccion"])
        if "telefono_extra" in updates:
            worksheet.update_cell(row, 10, updates["telefono_extra"])
        if "ruta_asignada" in updates:
            worksheet.update_cell(row, 11, updates["ruta_asignada"])
        if "producto" in updates:
            worksheet.update_cell(row, 12, updates["producto"])
            
        return True
        
    def delete_client(self, client_id: str) -> bool:
        """Delete a client row from CLIENTES sheet"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("CLIENTES")
        
        cell = worksheet.find(client_id)
        if not cell:
            return False # Not found
            
        worksheet.delete_rows(cell.row)
        return True
    
    def get_special_prices(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get special prices, optionally filtered by client"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PRECIOS_ESPECIALES")
        records = self._get_all_records_safe(worksheet)
        
        if client_id:
            records = [r for r in records if r.get("ID_Cliente") == client_id]
        
        return records
    
    def get_price_for_client_product(self, client_id: str, product: str, base_price: float) -> float:
        """Get the price for a client+product combination, or return base price"""
        prices = self.get_special_prices(client_id)
        for price in prices:
            if price.get("Producto") == product:
                return float(price.get("Precio_Pactado", base_price))
        return base_price
    
    def create_special_price(self, client_id: str, product: str, price: float) -> str:
        """Create a special price rule"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PRECIOS_ESPECIALES")
        
        rule_id = f"PRE-{uuid.uuid4().hex[:8].upper()}"
        
        row = [rule_id, client_id, product, price]
        worksheet.append_row(row)
        
        return rule_id
    
    # ============ PROSPECTOS ============
    
    def create_prospect(self, data: Dict[str, Any]) -> str:
        """Create a new prospect"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PROSPECTOS")
        
        prospect_id = f"PROS-{uuid.uuid4().hex[:8].upper()}"
        
        row = [
            prospect_id,
            data.get("nombre_negocio", "Nuevo Prospecto"),
            data.get("direccion", ""),
            data.get("latitud", 0),
            data.get("longitud", 0),
            "Pendiente", # Estatus
            datetime.now().strftime("%Y-%m-%d"),
            data.get("interes_producto", "Queso Oaxaca"), # Default Interest
            data.get("precio_oferta", 160.0), # Default Offer Price
            data.get("fecha_ruta", "") # Fecha Ruta assigned
        ]
        
        worksheet.append_row(row)
        return prospect_id

    def get_pending_prospects(self, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get prospects with status 'Pendiente'.
        If target_date is provided, only include those with MATCHING date OR empty date (backlog).
        """
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PROSPECTOS")
        records = self._get_all_records_safe(worksheet)
        
        pending = [r for r in records if r.get("Estatus") == "Pendiente"]
        
        if target_date:
            print(f"DEBUG: Filtering prospects for date: '{target_date}'")
            # Filter logic:
            # 1. Include if "Fecha_Ruta" is missing/empty (Global backlog)
            # 2. Include if "Fecha_Ruta" matches target_date
            
            filtered = []
            for r in pending:
                fecha_row = str(r.get("Fecha_Ruta", "")).strip()
                # Debug comparison
                if not fecha_row or fecha_row == target_date:
                    filtered.append(r)
                else:
                    # Optional: Print ignored ones to see why
                    # print(f"DEBUG: Ignoring prospect {r.get('Nombre_Negocio')} date='{fecha_row}' != '{target_date}'")
                    pass
            
            print(f"DEBUG: Found {len(filtered)} prospects matching date (or backlog)")
            return filtered
            
        print(f"DEBUG: No target date, returning all {len(pending)} pending prospects")
        return pending

    def delete_prospect(self, prospect_id: str) -> bool:
        """Delete a prospect row by ID"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PROSPECTOS")
        try:
            cell = worksheet.find(prospect_id)
            worksheet.delete_rows(cell.row)
            return True
        except gspread.exceptions.CellNotFound:
            print(f"Prospecto {prospect_id} no encontrado para eliminar.")
            return False
            
    def mark_prospect_visited(self, prospect_id: str) -> bool:
        """Mark a prospect as visited/converted"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PROSPECTOS")
        
        cell = worksheet.find(prospect_id)
        if not cell:
            return False
            
        # Estatus is index 6 (Column F)
        worksheet.update_cell(cell.row, 6, "Visitado")
        return True
    
    # ============ PEDIDOS ============
    
    def get_orders_by_date(self, fecha_ruta: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get orders for a specific date, optionally filtered by status"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        records = self._get_all_records_safe(worksheet)
        
        # Filter by date
        filtered = [r for r in records if r.get("Fecha_Ruta") == fecha_ruta]
        
        # Filter by status if provided
        if status:
            filtered = [r for r in filtered if r.get("Estatus") == status]
        
        return filtered
    
    def get_orders_for_optimization(self, fecha_ruta: str) -> List[Dict[str, Any]]:
        """Get orders ready for route optimization (Confirmado OR Pendiente status)"""
        # Fetch all orders for the date first
        print(f"DEBUG: Fetching orders for date '{fecha_ruta}'...")
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        records = self._get_all_records_safe(worksheet)
        
        # Debug Date Matching
        matching_date_count = 0
        for r in records:
             if str(r.get("Fecha_Ruta")).strip() == fecha_ruta:
                 matching_date_count += 1
             
        print(f"DEBUG: Found {matching_date_count} records matching date '{fecha_ruta}'. Total records: {len(records)}")
        
        # Filter by date
        # Use loose matching for safety: strip strings
        all_orders = [r for r in records if str(r.get("Fecha_Ruta")).strip() == fecha_ruta.strip()]
        
        # Filter for active statuses (case insensitive just in case)
        # Often new orders start as "Pendiente" until reviewed.
        # "En Ruta" allowed for re-optimization.
        valid_statuses = ["confirmado", "pendiente", "preventa", "en ruta"]
        orders = []
        
        for o in all_orders:
            status = str(o.get("Estatus", "")).strip().lower()
            if status in valid_statuses:
                orders.append(o)
            else:
                print(f"DEBUG: Skipping order {o.get('ID_Pedido')} - Status '{status}' not in {valid_statuses}")
        
        print(f"DEBUG: get_orders_for_optimization returns {len(orders)} active orders.")
        
        # Enrich with client data
        clients = {c["ID_Cliente"]: c for c in self.get_all_clients()}
        
        for order in orders:
            client = clients.get(order.get("ID_Cliente"))
            if client:
                order["Latitud"] = client.get("Latitud")
                order["Longitud"] = client.get("Longitud")
                order["Nombre_Negocio"] = client.get("Nombre_Negocio")
                order["Telefono"] = client.get("Telefono")
                order["Zona"] = client.get("Zona")
            else:
                 print(f"DEBUG: WARNING - Client {order.get('ID_Cliente')} NOT FOUND for Order {order.get('ID_Pedido')}")
        
        return orders
    
    def create_order(self, order_data: Dict[str, Any]) -> str:
        """Create a new order"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        
        order_id = f"PED-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate price (Clean product name first: "Oaxaca (20kg)" -> "Oaxaca")
        product_raw = order_data.get("producto", "")
        # Remove (Xkg) case insensitive
        # Matches: space(opt) + ( + digits + .digits(opt) + kg/KG + )
        import re
        product_clean = re.sub(r'\s*\(\d+(\.\d+)?\s*[kK][gG]\)', '', product_raw).strip()
        
        price = self.get_price_for_client_product(
            order_data.get("id_cliente", ""),
            product_clean,
            100.0  # Base price fallback
        )
        
        row = [
            order_id,
            order_data.get("fecha_ruta", ""),
            order_data.get("id_cliente", ""),
            "Preventa",  # Initial status
            "",  # Orden_Visita (empty, filled by optimizer)
            order_data.get("producto", ""),
            order_data.get("kg_solicitados", 0),
            "",  # Kg_Reales
            price,
            "",  # Total_Cobrar (calculated on delivery)
            ""   # Timestamp_Entrega
        ]
        
        worksheet.append_row(row)
        return order_id
    
    def update_visit_order(self, order_id: str, visit_order: int) -> bool:
        """Update the Orden_Visita field for an order"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        
        # Find the row
        cell = worksheet.find(order_id)
        if not cell:
            return False
        
        # Orden_Visita is column 5 (E)
        worksheet.update_cell(cell.row, 5, visit_order)
        return True
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update the status of an order"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        
        cell = worksheet.find(order_id)
        if not cell:
            return False
        
        # Estatus is column 4 (D)
        worksheet.update_cell(cell.row, 4, status)
        return True

    def delete_order(self, order_id: str) -> bool:
        """Delete an order row from PEDIDOS sheet and decrement Client Counter"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        
        try:
            cell = worksheet.find(order_id)
            if not cell:
                return False
            
            # 1. Get Client ID before deleting (Column 3 is ID_Cliente)
            id_cliente = worksheet.cell(cell.row, 3).value
            
            # 2. Delete Order Row
            worksheet.delete_rows(cell.row)
            
            # 3. Decrement Client Counter
            if id_cliente:
                try:
                    client_ws = self._spreadsheet.worksheet("CLIENTES")
                    client_cell = client_ws.find(id_cliente)
                    if client_cell:
                        # Contador_Ventas is Column 9 (I)
                        current_val_str = client_ws.cell(client_cell.row, 9).value
                        current_val = int(current_val_str) if current_val_str and current_val_str.isdigit() else 0
                        
                        # Only decrement, don't go below 0 (though 0 shouldn't happen if deleting an order)
                        new_val = max(0, current_val - 1)
                        client_ws.update_cell(client_cell.row, 9, new_val)
                        print(f"✓ Contador decrementado para {id_cliente}: {current_val} -> {new_val}")
                except Exception as e:
                    print(f"⚠ Error decrementing counter for {id_cliente}: {e}")
            
            return True
        except gspread.exceptions.CellNotFound:
            return False
        except Exception as e:
            print(f"Error deleting order {order_id}: {e}")
            return False
    
    def complete_delivery(self, order_id: str, kg_reales: float) -> bool:
        """Mark an order as delivered with actual kg using batch update"""
        try:
            self.ensure_connected()
            worksheet = self._spreadsheet.worksheet("PEDIDOS")
            
            # DEBUG TRACING FOR 500 ERROR
            print(f"DEBUG: complete_delivery called for {order_id} with {kg_reales}kg")
            
            try:
                cell = worksheet.find(order_id.strip())
            except gspread.exceptions.CellNotFound:
                cell = None
            except Exception as e:
                print(f"DEBUG: Error finding cell for {order_id}: {e}")
                raise e
                
            if not cell:
                print(f"Order {order_id} not found in sheet")
                return False
            
            # 1. Get Order Data
            try:
                row_data = worksheet.row_values(cell.row)
            except Exception as e:
                print(f"DEBUG: Error reading row values for row {cell.row}: {e}")
                raise e
            
            if len(row_data) < 3:
                 print("Error: Row data too short to find Client ID")
                 return False
            
            id_cliente = row_data[2]  # Index 2 = Col C
            print(f"DEBUG: Found Client ID {id_cliente} for Order {order_id}")
            
            # 2. Get and Increment Client Counter
            folio_nota = 1
            client_ws = self._spreadsheet.worksheet("CLIENTES")
            client_cell = client_ws.find(id_cliente)
            
            if client_cell:
                # Column 9 (I) is Contador_Ventas
                current_val_str = client_ws.cell(client_cell.row, 9).value
                current_count = int(current_val_str) if current_val_str and current_val_str.isdigit() else 0
                
                folio_nota = current_count + 1
                # Update Client directly (single cell update is okay here)
                client_ws.update_cell(client_cell.row, 9, folio_nota)
                print(f"DEBUG: Updated client counter to {folio_nota}")
            else:
                print(f"DEBUG: Client {id_cliente} not found in CLIENTES sheet")
            
            # 3. Calculate Totals
            precio_unitario = 0.0
            # Price is Col I (9), which corresponds to Index 8
            # row_data[8]
            if len(row_data) > 8:
                 try:
                     val = row_data[8] # Price string "$120" or "120"
                     # Clean string if needed
                     if isinstance(val, str):
                         val = val.replace('$', '').replace(',', '').strip()
                     precio_unitario = float(val)
                 except ValueError:
                     precio_unitario = 0.0
                     
            total = float(kg_reales) * precio_unitario
            
            # 4. Batch Update Order Row
            # We want to update cols D(4), H(8), J(10), K(11), L(12)
            # Range D{row}:L{row} -> Cols 4, 5, 6, 7, 8, 9, 10, 11, 12
            # We must preserve values for 5(E), 6(F), 7(G), 9(I)
            
            # row_data indices:
            # 0=A, 1=B, 2=C, 3=D, 4=E, 5=F, 6=G, 7=H, 8=I, 9=J, 10=K, 11=L ...
            
            # Helper to safely get index or ""
            def get_idx(idx): return row_data[idx] if len(row_data) > idx else ""

            # Construct new values for the range components
            # Col 4 (D) Status
            val_d = "Entregado"
            # Col 5 (E) Orden
            val_e = get_idx(4)
            # Col 6 (F) Producto
            val_f = get_idx(5) 
            # Col 7 (G) Kg Solicitados
            val_g = get_idx(6)
            # Col 8 (H) Kg Reales -> NEW
            val_h = float(kg_reales)
            # Col 9 (I) Precio
            val_i = get_idx(8)
            # Col 10 (J) Total -> NEW
            val_j = total
            # Col 11 (K) Timestamp -> NEW
            val_k = datetime.now().isoformat()
            # Col 12 (L) Folio -> NEW
            val_l = int(folio_nota)

            # Update range D:L
            update_range = f"D{cell.row}:L{cell.row}"
            values = [[val_d, val_e, val_f, val_g, val_h, val_i, val_j, val_k, val_l]]
            
            print(f"DEBUG: Updating range {update_range} with values: {values}")
            
            # Gspread update expects (range_name, values)
            try:
                # Try modern signature
                worksheet.update(range_name=update_range, values=values)
            except TypeError:
                print("DEBUG: update() failed with named args, trying positional")
                # Fallback for older gspread versions which might accept positional differently
                # or if named args aren't supported (unlikely in recent versions)
                worksheet.update(update_range, values)
            except Exception as e:
                print(f"DEBUG: Error executing update(): {e}")
                raise e
                
            print(f"✓ Order {order_id} completed. Folio: {folio_nota}")
            return True

        except Exception as e:
            print(f"CRITICAL ERROR in complete_delivery: {traceback.format_exc()}")
            # Re-raise so endpoint returns 500 with detail, but at least we logged it
            raise e
    
    def batch_update_visit_orders(self, updates: List[Dict[str, Any]]) -> int:
        """
        Batch update visit orders for multiple orders.
        updates format: [{"order_id": "...", "orden_visita": 1}, ...]
        Returns number of successful updates.
        """
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        
        success_count = 0
        for update in updates:
            try:
                cell = worksheet.find(update["order_id"])
                if cell:
                    worksheet.update_cell(cell.row, 5, update["orden_visita"])
                    # Also update status to "En Ruta"
                    worksheet.update_cell(cell.row, 4, "En Ruta")
                    success_count += 1
            except Exception as e:
                print(f"Error updating {update['order_id']}: {e}")
        
        return success_count

    # ============ WEEKLY SUMMARY ============
    
    def get_weekly_purchase_summary(self) -> Dict[str, float]:
        """Get aggregated kg by product for all Preventa orders this week"""
        self.ensure_connected()
        worksheet = self._spreadsheet.worksheet("PEDIDOS")
        records = self._get_all_records_safe(worksheet)
        
        # Filter for Preventa status
        preventa = [r for r in records if r.get("Estatus") == "Preventa"]
        
        # Aggregate by product
        summary = {}
        for order in preventa:
            product = order.get("Producto", "")
            kg = float(order.get("Kg_Solicitados", 0))
            summary[product] = summary.get(product, 0) + kg
        
        return summary
