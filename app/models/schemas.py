"""
Pydantic models for the logistics API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class OrderStatus(str, Enum):
    PREVENTA = "Preventa"
    CONFIRMADO = "Confirmado"
    EN_RUTA = "En Ruta"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"


class Location(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class Client(BaseModel):
    id_cliente: str = Field(..., alias="ID_Cliente")
    nombre_negocio: str = Field(..., alias="Nombre_Negocio")
    telefono: str = Field(..., alias="Telefono")
    latitud: float = Field(..., alias="Latitud")
    longitud: float = Field(..., alias="Longitud")
    zona: Optional[str] = Field(None, alias="Zona")
    fecha_alta: Optional[str] = Field(None, alias="Fecha_Alta")
    direccion: Optional[str] = Field(None, alias="Direccion")
    telefono_extra: Optional[str] = Field(None, alias="Telefono_Extra")
    ruta_asignada: Optional[str] = Field(None, alias="Ruta_Asignada")

    class Config:
        populate_by_name = True


class SpecialPrice(BaseModel):
    id_regla: str = Field(..., alias="ID_Regla")
    id_cliente: str = Field(..., alias="ID_Cliente")
    producto: str = Field(..., alias="Producto")
    precio_pactado: float = Field(..., alias="Precio_Pactado")

    class Config:
        populate_by_name = True


class Order(BaseModel):
    id_pedido: str = Field(..., alias="ID_Pedido")
    fecha_ruta: str = Field(..., alias="Fecha_Ruta")
    id_cliente: str = Field(..., alias="ID_Cliente")
    estatus: OrderStatus = Field(..., alias="Estatus")
    orden_visita: Optional[int] = Field(None, alias="Orden_Visita")
    producto: str = Field(..., alias="Producto")
    kg_solicitados: float = Field(..., alias="Kg_Solicitados")
    kg_reales: Optional[float] = Field(None, alias="Kg_Reales")
    precio_unitario: Optional[float] = Field(None, alias="Precio_Unitario")
    total_cobrar: Optional[float] = Field(None, alias="Total_Cobrar")
    timestamp_entrega: Optional[str] = Field(None, alias="Timestamp_Entrega")
    
    # Joined fields from CLIENTES
    nombre_negocio: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None

    class Config:
        populate_by_name = True


class CreateClientRequest(BaseModel):
    nombre_negocio: str
    telefono: str
    latitud: float
    longitud: float
    zona: Optional[str] = None
    direccion: Optional[str] = None
    producto: Optional[str] = None
    precio_pactado: Optional[float] = None
    telefono_extra: Optional[str] = None
    ruta_asignada: Optional[str] = None


class CreateOrderRequest(BaseModel):
    id_cliente: str
    fecha_ruta: str
    producto: str
    kg_solicitados: float


class OptimizeRouteRequest(BaseModel):
    fecha_ruta: str
    test_mode: bool = False
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None


class OptimizeRouteResponse(BaseModel):
    success: bool
    message: str
    optimized_order: List[dict] = []
    total_distance_km: Optional[float] = None
    total_time_minutes: Optional[float] = None


class DeliveryNode(BaseModel):
    """Node for route optimization"""
    id: str
    name: str
    lat: float
    lng: float
    is_waypoint: bool = False  # True for Huichapan security waypoint
    is_depot: bool = False     # True for warehouse/origin
