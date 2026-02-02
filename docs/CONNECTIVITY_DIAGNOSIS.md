# Diagnóstico y Resolución de Conectividad Remota (Cloudflare Tunnel)

## 1. Descripción del Problema

### Contexto
El objetivo era permitir que la aplicación móvil "El Hidalguense" funcionara no solo en la red local (WiFi de casa), sino **desde cualquier lugar** (acceso remoto), conectándose al servidor central en la Mac del usuario. Para lograr esto de manera segura y sin abrir puertos en el router, utilizamos **Cloudflare Tunnel**.

### Síntomas
A pesar de que el servidor (Backend) se iniciaba correctamente y reportaba estar "Healthy" (saludable), la aplicación móvil mostraba persistentemente el estado **"OFFLINE"**.

Al intentar acceder a la URL pública generada por el túnel (`https://....trycloudflare.com`), se observaron los siguientes comportamientos erráticos:
1.  **Error 530 (Origin Unreachable):** Cloudflare informaba que no podía alcanzar el servidor de origen.
2.  **Error 000 (Connection Failed):** Las herramientas de diagnóstico (`curl`) fallaban al intentar conectar con el túnel, devolviendo un código de estado 000, indicando que la conexión ni siquiera se establecía.
3.  **Tiempos de espera (Timeouts):** El proceso de creación del túnel a veces se quedaba "colgado" indefinidamente sin generar una URL.

---

## 2. Metodología de Investigación

Para llegar a la causa raíz, seguimos un proceso de eliminación sistemático, descartando posibles fallos uno a uno.

### Fase 1: Verificación del Servidor Local (Backend)
**Hipótesis:** El servidor Python (FastAPI) no se está ejecutando o está fallando.
**Prueba:** Ejecutamos una petición directa al servidor local:
```bash
curl -v http://127.0.0.1:8000/api/health
```
**Resultado:** El servidor respondió inmediatamente con `HTTP 200 OK` y el estado `{"status": "healthy"}`.
**Conclusión:** El Backend funciona perfectamente. El problema está en el "puente" (el túnel) hacia internet.

### Fase 2: Análisis de Conflictos de Procesos
**Hipótesis:** Existen múltiples instancias de `cloudflared` (procesos "zombie") peleando por el mismo recurso o puerto.
**Prueba:** Buscamos y eliminamos agresivamente cualquier proceso existente:
```bash
pkill -9 cloudflared
ps aux | grep cloudflared
```
**Resultado:** Se limpiaron los procesos, pero al reiniciar el túnel, el problema persistía.
**Conclusión:** No es un conflicto de procesos locales.

### Fase 3: Diagnóstico en Profundidad (Logs de Depuración)
**Hipótesis:** La red (ISP o Router) está bloqueando el protocolo de comunicación del túnel.
**Prueba:** Ejecutamos el túnel en modo "verbose" (detallado) para ver la negociación de la conexión:
```bash
cloudflared tunnel --url http://127.0.0.1:8000 --loglevel debug
```
**Hallazgo Crítico:** 
Los logs mostraron lo siguiente:
```
2026-01-20T10:59:07Z INF Settings: map[protocol:quic ...]
2026-01-20T10:59:07Z INF Requesting new quick Tunnel...
(El proceso se detiene aquí y nunca confirma la conexión)
```
Cloudflare intenta usar por defecto el protocolo **QUIC** (basado en UDP). La ausencia de una confirmación de "Registered tunnel connection" indicó que estos paquetes UDP estaban siendo **bloqueados silenciosamente** por el proveedor de internet (ISP) o el firewall del router.

---

## 3. Causa Raíz: Bloqueo del Protocolo QUIC

El protocolo **QUIC** (Quick UDP Internet Connections) es una tecnología moderna que Cloudflare utiliza para mejorar la velocidad. Sin embargo, tiene una desventaja significativa:
*   Utiliza **UDP** en lugar de TCP.
*   Muchos proveedores de internet corporativos o residenciales, así como firewalls estrictos, **bloquean el tráfico UDP desconocido** por motivos de seguridad o gestión de tráfico.

Al bloquearse el tráfico UDP, el túnel intentaba "hablar" con Cloudflare pero nunca recibía respuesta, resultando en un "túnel zombie" que existía pero no transmitía datos (Error 530).

---

## 4. Solución Implementada: Forzar Protocolo HTTP2

Para solucionar esto, instruimos explícitamente a `cloudflared` para que **no utilice QUIC**, sino que fuerce el uso del protocolo **HTTP2**.

### ¿Por qué funciona HTTP2?
*   HTTP2 utiliza **TCP** estándar (el mismo protocolo que usan todas las páginas web normales).
*   Se encapsula sobre HTTPS (Puerto 443).
*   Para un firewall o ISP, el tráfico de HTTP2 parece tráfico web normal y corriente, por lo que **casi nunca es bloqueado**.

### Cambio en el Código
Modificamos el script de arranque (`mobile/start_mobile_remote.command`) para incluir la bandera `--protocol http2`:

**Antes (Fallaba):**
```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

**Después (Funciona):**
```bash
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2
```

### Verificación del Éxito
Al ejecutar la prueba con HTTP2 (`debug_tunnel_http2.log`), los logs confirmaron el éxito inmediato:
```
2026-01-20T10:59:29Z INF Initial protocol http2
2026-01-20T10:59:29Z INF Registered tunnel connection ... protocol=http2
```
La conexión se estableció en milisegundos y se mantuvo estable.

---

## 5. Prevención y Mantenimiento

### Mecanismo de Autocuración (Self-Healing)
Además de forzar el protocolo, hemos "blindado" el script de arranque (`start_mobile_remote.command`) con las siguientes mejoras de robustez:

1.  **Limpieza Agresiva:** Al inicio, ejecuta `pkill -9 cloudflared` para asegurar un estado limpio.
2.  **Verificación Activa:** Antes de mostrarte el código QR, el script realiza un **Test de Conexión Interno**.
    *   Intenta acceder a tu propia URL pública (`https://....trycloudflare.com/api/health`).
    *   Si no recibe un `HTTP 200 OK`, sabe que el túnel falló y te avisa, en lugar de dejarte escanear un QR que no funcionará.
3.  **IPv4 Forzado:** Se fuerza el uso de `127.0.0.1` en lugar de `localhost` para evitar ambigüedades en la resolución de nombres del sistema.

Con esta configuración, el sistema es ahora **resiliente a bloqueos de red** y garantiza que, si ves el código QR, la conexión remota es funcional.
