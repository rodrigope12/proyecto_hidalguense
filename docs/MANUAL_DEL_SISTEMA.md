# Manual del Sistema Integral de Logística y Distribución "El Hidalguense"

**Versión del Documento:** 1.0  
**Fecha de Última Actualización:** 20 de Enero de 2026  

---

## ÍNDICE DE CONTENIDOS

1.  [Introducción y Visión General](#1-introducción-y-visión-general)
2.  [Arquitectura Técnica del Sistema](#2-arquitectura-técnica-del-sistema)
3.  [Requisitos Previos e Instalación](#3-requisitos-previos-e-instalación)
4.  [Guía de Operación Diaria (Arrancador Universal)](#4-guía-de-operación-diaria)
5.  [Manual de Usuario: Aplicación Móvil](#5-manual-de-usuario-aplicación-móvil)
6.  [Manual de Usuario: Panel Web](#6-manual-de-usuario-panel-web)
7.  [Diagnóstico y Solución de Problemas (Troubleshooting)](#7-diagnóstico-y-solución-de-problemas)
8.  [Guía para Desarrolladores](#8-guía-para-desarrolladores)

---

## 1. INTRODUCCIÓN Y VISIÓN GENERAL

Este sistema ha sido diseñado específicamente para modernizar y optimizar la logística de última milla de "El Hidalguense". Su objetivo principal es transformar un proceso manual basado en hojas de cálculo y conocimiento empírico en una operación digitalizada, eficiente y basada en datos.

El sistema resuelve tres problemas críticos:
1.  **Optimización de Rutas:** Calcula automáticamente el orden ideal de visitas para minimizar tiempo y combustible, respetando restricciones de seguridad (paso obligatorio por Huichapan).
2.  **Digitalización de Pedidos y Entregas:** Reemplaza las notas de papel por una aplicación móvil que permite levantar pedidos, registrar ventas y capturar la ubicación exacta de los clientes.
3.  **Conectividad Remota:** Permite operar el sistema desde cualquier lugar de la república, conectando los dispositivos móviles de los repartidores con el servidor central de la oficina mediante túneles seguros.

---

## 2. ARQUITECTURA TÉCNICA DEL SISTEMA

El sistema sigue una arquitectura moderna de microservicios acoplados, diseñada para ser robusta y fácil de mantener.

### Componentes Principales

1.  **Backend (El Cerebro):**
    *   **Tecnología:** Python con FastAPI.
    *   **Función:** Procesa toda la lógica de negocio, cálculos de rutas (algoritmo VRP con OR-Tools), y gestión de datos.
    *   **Puerto Local:** 8000.

2.  **Base de Datos (El Almacén):**
    *   **Tecnología:** Google Sheets (API V4).
    *   **Función:** Actúa como base de datos en tiempo real. Esto permite que el administrador vea y edite los datos (Pedidos, Clientes) directamente en Excel/Sheets sin necesitar conocimientos de SQL.

3.  **Frontend Web (El Tablero de Control):**
    *   **Tecnología:** HTML5, JS Vanilla, CSS Moderno.
    *   **Función:** Interfaz visual para que el administrador monitoree las rutas en un mapa interactivo y gestione la operación desde la oficina. Provisión de archivos estáticos servidos por el Backend.

4.  **Aplicación Móvil (La Herramienta del Repartidor):**
    *   **Tecnología:** React Native con Expo.
    *   **Función:** Interfaz táctil para el repartidor. Funciona en Android e iOS. Permite ver la ruta, navegar con Google Maps, y registrar entregas.
    *   **Conexión:** Se conecta al backend mediante API REST.

5.  **Capa de Conectividad (El Puente):**
    *   **Tecnología:** Cloudflare Tunnel (`cloudflared`).
    *   **Función:** Expone el servidor local (que está en una Mac detrás de un router doméstico) a internet de forma segura y encriptada, generando una URL pública (`https://....trycloudflare.com`). **Ahora configurado con protocolo HTTP2 para evitar bloqueos.**

---

## 3. REQUISITOS PREVIOS E INSTALACIÓN

Para ejecutar este sistema en un nuevo equipo (Mac), se requiere lo siguiente:

### Software Base
*   **Python 3.9+:** Para ejecutar el backend.
*   **Node.js & NPM:** Para ejecutar el entorno de desarrollo móvil (Expo).
*   **Cloudflared:** Binario oficial de Cloudflare para crear los túneles.

### Credenciales (Archivos Sensibles)
Estos archivos son las "llaves" del sistema y no deben compartirse:
1.  `credentials/service_account.json`: Permiso de Google Cloud para leer/escribir en Sheets.
2.  `.env`: Archivo de configuración con claves API (Google Maps, IDs de hojas de cálculo).

### Instalación de Dependencias
1.  **Backend:** `pip install -r requirements.txt` (dentro del entorno virtual `venv`).
2.  **Móvil:** `cd mobile && npm install`.

---

## 4. GUÍA DE OPERACIÓN DIARIA

Hemos simplificado el arranque de todo el sistema en un solo comando unificado. Ya no es necesario abrir 4 terminales diferentes.

### Pasos para Iniciar el Día
1.  Encienda la Mac principal (Servidor).
2.  Abra la carpeta del proyecto.
3.  Haga doble clic en el archivo **`start_all.command`**.

### ¿Qué hace `start_all.command`?
Este script es un orquestador inteligente que realiza las siguientes acciones secuenciales:
1.  **Limpieza:** Ejecuta `pkill` para cerrar cualquier proceso "zombie" anterior que pudiera bloquear los puertos.
2.  **Backend:** Inicia el servidor Python en segundo plano (`uvicorn app.main:app`).
3.  **Verificación de Salud:** Espera a que el backend responda con "Healthy" antes de continuar.
4.  **Túnel de Datos:** Inicia `cloudflared` forzando el protocolo **HTTP2** (crucial para evitar errores 530). Verifica activamente que la URL pública sea alcanzable desde internet.
5.  **Entorno Móvil:** Inicia Expo en modo LAN/WiFi y genera el código QR.

**Resultado:** Verá una ventana de terminal con un código QR gigante. Eso significa que el sistema está listo.

---

## 5. MANUAL DE USUARIO: APLICACIÓN MÓVIL

### Conexión Inicial
1.  Asegúrese de que el celular y la Mac estén en la misma red WiFi (para la descarga inicial del código).
2.  Abra la app "Expo Go" en su Android/iOS.
3.  Escanee el código QR que muestra la terminal de la Mac.
4.  La app se descargará e instalará en segundos.

### Uso en Ruta (Fuera de Casa)
Una vez cargada, la app **YA NO necesita el WiFi**. Utiliza la conexión de datos (4G/5G) del celular para comunicarse con la Mac a través del túnel seguro de Cloudflare.
*   **Pantalla "Ruta":** Muestra la lista ordenada de clientes a visitar hoy.
*   **Botón "Navegar":** Abre Google Maps con la ruta hacia el siguiente cliente.
*   **Registro de Entrega:** Al llegar, permite ingresar los Kilos Reales vendidos y marca el pedido como "Entregado" en tiempo real en el Google Sheet.

---

## 6. MANUAL DE USUARIO: PANEL WEB

Accesible desde `http://localhost:8000` en la Mac.

*   **Mapa en Vivo:** Muestra pines de colores (Amarillo: Pendiente, Verde: Entregado, Rojo: Fallido).
*   **Gestión de Clientes:** Permite dar de alta nuevos clientes que se sincronizan con la app móvil.
*   **Optimización:** Un botón que recalcula la ruta óptima del día basándose en los pedidos registrados en Google Sheets hasta ese momento.

---

## 7. DIAGNÓSTICO Y SOLUCIÓN DE PROBLEMAS

Esta sección documenta los problemas históricos y sus soluciones definitivas.

### Problema Crítico: "App Offline / Error 530"
**Síntoma:** La app carga pero muestra un banner rojo "OFFLINE".
**Causa Técnica:** El proveedor de internet (ISP) bloqueaba el protocolo **QUIC (UDP)** que Cloudflare usa por defecto. Esto creaba un túnel que parecía activo pero no transmitía datos (Error 530 Origin Unreachable).
**Solución Aplicada:** El lanzador ahora incluye la bandera `--protocol http2` al iniciar el túnel. Esto encapsula el tráfico en TCP/HTTPS estándar, haciéndolo indistinguible de la navegación web normal y evitando el bloqueo.
**Verificación:** Si esto vuelve a suceder, ejecute `mobile/start_mobile_remote.command` y observe si aparece el mensaje `✅ Túnel verificado (HTTP 200 OK)`.

### Problema: "No se puede descargar la actualización remota"
**Síntoma:** Pantalla roja en el celular al intentar abrir la app.
**Causa:** El celular no puede ver a la computadora para descargar el código JavaScript (Bundle).
**Solución:**
1.  Asegúrese de estar en el **mismo WiFi**.
2.  Verifique que no haya firewalls bloqueando el puerto 8081 en la Mac.
3.  Reinicie el router WiFi si la red está inestable.

### Problema: Datos no se guardan en Google Sheets
**Causa:** El archivo `credentials/service_account.json` puede haber expirado o estar dañado, o la Mac perdió conexión a internet.
**Solución:** Verifique la conexión a internet de la Mac. Si persiste, regenere la llave de servicio en la consola de Google Cloud.

---

## 8. GUÍA PARA DESARROLLADORES

### Estructura de Directorios (Limpia)
*   **`/app`**: Código fuente del Backend (Python).
    *   `main.py`: Punto de entrada (`FastAPI`).
    *   `optimization/vrp_solver.py`: Lógica matemática de rutas.
    *   `integrations/`: Conectores con Google y Cloudflare.
*   **`/mobile`**: Código fuente de la App (React Native).
    *   `App.js`: Componente raíz y navegación.
    *   `src/screens`: Pantallas individuales (Mapa, Pedidos, etc.).
    *   `src/api/client.js`: Cliente HTTP (Axios) configurado dinámicamente por el script de arranque.
*   **`/docs`**: Documentación del sistema.

### Cómo Agregar una Nueva Funcionalidad
1.  **Backend:** Agregue el endpoint en `app/main.py` y defina el modelo de datos en `app/models/schemas.py`.
2.  **Móvil:** Agregue la función de consumo en `mobile/src/api/client.js` y cree la interfaz visual en `mobile/src/screens`.
3.  **Despliegue:** Solo requiere reiniciar `start_all.command` para que los cambios se reflejen.

### Notas de Mantenimiento
*   No edite manualmente `mobile/src/api/client.js` la línea `API_BASE_URL`, ya que el script de arranque la sobrescribe automáticamente en cada inicio.
*   Para actualizar librerías: `pip freeze > requirements.txt` después de instalar algo nuevo en Python.

---
**Fin del Manual**
