# Configuración de Google Sheets para Sistema Última Milla

Este documento explica cómo crear las hojas de cálculo necesarias para el sistema.

## Crear Spreadsheet

1. Ve a [Google Sheets](https://sheets.google.com)
2. Crea un nuevo documento: **"Última Milla - Logística"**
3. Copia el ID del spreadsheet desde la URL:
   ```
   https://docs.google.com/spreadsheets/d/[ESTE_ES_EL_ID]/edit
   ```
4. Pega el ID en el archivo `.env` en la variable `SPREADSHEET_ID`

## Hojas Requeridas

### 1. CLIENTES (Hoja 1)

Renombra la primera hoja a `CLIENTES` y crea estas columnas:

| Columna | Tipo | Ejemplo |
|---------|------|---------|
| ID_Cliente | Texto | CLI-A1B2C3D4 |
| Nombre_Negocio | Texto | Cremería La Esperanza |
| Telefono | Texto | 5551234567 |
| Latitud | Número | 20.1234 |
| Longitud | Número | -99.5678 |
| Zona | Texto | Centro |
| Fecha_Alta | Fecha | 2026-01-12 |

### 2. PRECIOS_ESPECIALES (Hoja 2)

Crea una nueva hoja llamada `PRECIOS_ESPECIALES`:

| Columna | Tipo | Ejemplo |
|---------|------|---------|
| ID_Regla | Texto | PRE-X1Y2Z3 |
| ID_Cliente | Texto | CLI-A1B2C3D4 |
| Producto | Texto | Queso Oaxaca |
| Precio_Pactado | Moneda | 95.00 |

### 3. PEDIDOS (Hoja 3)

Crea una nueva hoja llamada `PEDIDOS`:

| Columna | Tipo | Ejemplo |
|---------|------|---------|
| ID_Pedido | Texto | PED-M1N2O3 |
| Fecha_Ruta | Fecha | 2026-01-18 |
| ID_Cliente | Texto | CLI-A1B2C3D4 |
| Estatus | Texto | Confirmado |
| Orden_Visita | Número | (vacío, llenado por optimizador) |
| Producto | Texto | Queso Oaxaca |
| Kg_Solicitados | Número | 5.5 |
| Kg_Reales | Número | (vacío, llenado al entregar) |
| Precio_Unitario | Moneda | 95.00 |
| Total_Cobrar | Moneda | (fórmula: Kg_Reales * Precio) |
| Timestamp_Entrega | Fecha/Hora | (vacío, llenado al entregar) |

## Permisos

1. Comparte el spreadsheet con el Service Account
2. El email está en tu archivo `service_account.json` en el campo `client_email`
3. Dale permiso de **Editor**

## Valores de Estatus

- `Preventa` - Pedido registrado, pendiente de confirmación
- `Confirmado` - Listo para optimización de ruta
- `En Ruta` - Ruta optimizada, conductor en camino
- `Entregado` - Entrega completada
- `Cancelado` - Pedido cancelado
