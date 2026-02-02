/**
 * Sistema El Hidalguense - Logística
 * App PWA para distribuidora de quesos artesanales
 */

// ============ State ============
const state = {
    orders: [],
    optimizedRoute: [],
    currentDeliveryIndex: 0,
    map: null,
    markers: [],
    routePath: null,
    isNavigating: false,
    demoMode: false
};

// ============ API Configuration ============
function getApiBase() {
    const serverIp = localStorage.getItem('serverIp') || window.location.hostname;
    // If accessing locally or same host, use relative path
    if (serverIp === window.location.hostname || serverIp === 'localhost') {
        return '';
    }
    // Otherwise, connect to the configured server
    return `http://${serverIp}:8000`;
}

const API_BASE = getApiBase();

// ============ Initialize ============
function initMap() {
    // Default to Mexico City area
    const defaultCenter = { lat: 20.0, lng: -99.5 };

    if (window.google) {
        state.map = new google.maps.Map(document.getElementById('map'), {
            center: defaultCenter,
            zoom: 8,
            styles: getMapStyles(),
            disableDefaultUI: true,
            zoomControl: true,
            mapTypeControl: false,
            streetViewControl: false
        });
        console.log('✓ Map initialized');
    }

    // Set today's date
    setToday();
}

function getMapStyles() {
    // Dark theme map styles
    return [
        { elementType: 'geometry', stylers: [{ color: '#1d2c4d' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#8ec3b9' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#1a3646' }] },
        {
            featureType: 'road',
            elementType: 'geometry',
            stylers: [{ color: '#304a7d' }]
        },
        {
            featureType: 'road',
            elementType: 'geometry.stroke',
            stylers: [{ color: '#1f2835' }]
        },
        {
            featureType: 'water',
            elementType: 'geometry',
            stylers: [{ color: '#0e1626' }]
        },
        {
            featureType: 'poi',
            elementType: 'geometry',
            stylers: [{ color: '#151c2c' }]
        }
    ];
}

// ============ Date Functions ============
function setToday() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('routeDate').value = today;
    loadOrders();
}

// ============ Data & Caching Functions ============
async function loadOrders() {
    const date = document.getElementById('routeDate').value;
    if (!date) return;

    // 1. Try Local Storage first (Offline Priority)
    const cachedKey = `orders_${date}`;
    const cachedData = localStorage.getItem(cachedKey);

    if (cachedData) {
        console.log('📦 Loading orders from cache');
        try {
            const data = JSON.parse(cachedData);
            state.orders = data.orders || [];
            state.demoMode = data.demo_mode; // might be undefined in old cache
            renderDeliveryList();
            updateStats();
            if (state.map) updateMapMarkers();
        } catch (e) { console.error("Cache parse error", e); }
    }

    // 2. Try to fetch fresh data if online
    if (navigator.onLine) {
        try {
            const apiBase = getApiBase();
            const response = await fetch(`${apiBase}/api/orders/${date}`);
            if (response.ok) {
                const data = await response.json();
                state.orders = data.orders || [];
                state.demoMode = data.demo_mode;

                // Update cache
                localStorage.setItem(cachedKey, JSON.stringify(data));

                renderDeliveryList();
                updateStats();
                if (state.map) updateMapMarkers();

                if (state.demoMode) {
                    showToast('Modo demo activo', 'warning');
                }
            }
        } catch (error) {
            console.log('Offline or API error, relying on cache');
            if (!cachedData) showToast('No se pudieron cargar los pedidos (Offline)', 'error');
        }
    }
}

async function optimizeRoute() {
    const btn = document.getElementById('optimizeBtn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width: 20px; height: 20px;"></div> Optimizando...';

    const date = document.getElementById('routeDate').value;
    const cacheKey = `route_${date}`;

    try {
        const apiBase = getApiBase();
        const response = await fetch(`${apiBase}/api/optimize-route`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha_ruta: date, test_mode: state.demoMode })
        });

        const data = await response.json();

        if (data.success) {
            state.optimizedRoute = data.optimized_order;

            // Cache the optimized route
            localStorage.setItem(cacheKey, JSON.stringify(data));

            // Update stats
            document.getElementById('totalDistance').textContent = data.total_distance_km || 0;
            document.getElementById('totalTime').textContent = data.total_time_minutes || 0;

            // Render optimized route
            renderOptimizedRoute();
            drawRouteOnMap();

            // Show navigation button
            document.getElementById('startNavBtn').style.display = 'flex';

            showToast('Ruta optimizada exitosamente (Guardada Local)', 'success');
        } else {
            showToast(data.message || 'Error al optimizar', 'error');
        }
    } catch (error) {
        console.error('Error optimization:', error);

        // Fallback: Check if we have a cached route
        const cachedRoute = localStorage.getItem(cacheKey);
        if (cachedRoute) {
            const data = JSON.parse(cachedRoute);
            state.optimizedRoute = data.optimized_order;
            renderOptimizedRoute();
            drawRouteOnMap();
            document.getElementById('startNavBtn').style.display = 'flex';
            showToast('Mostrando ruta guardada (Offline)', 'warning');
        } else {
            showToast('Error de conexión y sin ruta guardada', 'error');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🎯</span> Optimizar Ruta';
    }
}

// ============ Receipt Generation ============
async function generateReceiptImage(order, realKg, total) {
    // 1. Populate Template
    document.getElementById('receipt-remision').textContent = order.Orden_Visita || '001';
    document.getElementById('receipt-fecha').textContent = new Date().toLocaleDateString('es-MX');
    document.getElementById('receipt-cliente').textContent = order.Nombre_Negocio;
    document.getElementById('receipt-direccion').textContent = order.Zona || "Ubicación Registrada";

    document.getElementById('receipt-cant').textContent = realKg.toFixed(2);
    document.getElementById('receipt-producto').textContent = order.Producto;

    // Estimate price if not present (simplified logic)
    const pricePerKg = order.Precio_Unitario || 120.00;
    document.getElementById('receipt-precio').textContent = `$${pricePerKg.toFixed(2)}`;

    const calculatedTotal = total || (realKg * pricePerKg);
    const totalFormatted = `$${calculatedTotal.toFixed(2)}`;

    document.getElementById('receipt-total-row').textContent = totalFormatted;
    document.getElementById('receipt-subtotal').textContent = totalFormatted;
    document.getElementById('receipt-total-final').textContent = totalFormatted;

    // 2. Generate Canvas
    // Use the inner box. Wait for images to load if necessary.
    try {
        const element = document.querySelector('.receipt-box');
        const canvas = await html2canvas(element, {
            scale: 2,
            useCORS: true,
            allowTaint: true,
            backgroundColor: null
        });

        return new Promise(resolve => {
            canvas.toBlob(blob => {
                const cleanName = (order.Nombre_Negocio || 'Cliente').replace(/[^a-z0-9]/gi, '_').toLowerCase();
                const file = new File([blob], `Recibo_${cleanName}.png`, { type: 'image/png' });
                resolve(file);
            }, 'image/png');
        });
    } catch (e) {
        console.error("Error generating receipt", e);
        return null;
    }
}

async function completeDelivery(event) {
    event.preventDefault();
    const btn = event.target.querySelector('button[type="submit"]');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Generando Recibo...';

    const form = event.target;
    // Get Order ID from the hidden input
    const orderId = document.getElementById('deliveryOrderId').value;

    const kgReales = parseFloat(form.kg_reales.value);

    // Find order object
    const order = state.optimizedRoute.find(o => o.id === orderId) || state.orders.find(o => o.ID_Pedido === orderId);

    if (!order) {
        showToast("Error: Pedido no encontrado", "error");
        btn.disabled = false;
        btn.textContent = originalText;
        return;
    }

    // 1. Generate Receipt Image
    const receiptFile = await generateReceiptImage(order, kgReales);

    // 2. Construct WhatsApp Text
    const phone = order.Telefono || "5551234567";
    const totalEst = kgReales * 120; // Default price fallback
    const text = `Hola *${order.Nombre_Negocio}*\nAquí está su nota de entrega:\n🧀 ${order.Producto}: ${kgReales}kg\n💰 Total: $${totalEst}\n\n¡Gracias por su compra!`;

    // 3. Share flow
    if (receiptFile && navigator.canShare && navigator.canShare({ files: [receiptFile] })) {
        try {
            await navigator.share({
                files: [receiptFile],
                title: 'Recibo de Entrega',
                text: text
            });
            showToast('Recibo compartido', 'success');
        } catch (err) {
            console.log('Share dismissed', err);
        }
    } else if (receiptFile) {
        // Fallback: Download image then open WhatsApp
        const url = URL.createObjectURL(receiptFile);
        const a = document.createElement('a');
        a.href = url;
        a.download = receiptFile.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast('Recibo descargado. Abriendo WhatsApp...', 'info');

        setTimeout(() => {
            window.open(`https://wa.me/52${phone.replace(/\D/g, '')}?text=${encodeURIComponent(text)}`, '_blank');
        }, 1500);
    } else {
        // Just Text
        window.open(`https://wa.me/52${phone.replace(/\D/g, '')}?text=${encodeURIComponent(text)}`, '_blank');
    }

    // 4. Update Backend (Fire and forget)
    try {
        const apiBase = getApiBase();
        // Don't await, let it run
        fetch(`${apiBase}/api/orders/${orderId}/complete?kg_reales=${kgReales}`, { method: 'POST' })
            .catch(e => console.log('Sync failed, queuing for later'));
    } catch (e) { }

    // 5. Update Local State UI
    // Mark as delivered in local memory for immediate feedback
    const completedOrder = state.orders.find(o => o.ID_Pedido === orderId);
    if (completedOrder) completedOrder.Estatus = 'Entregado';

    hideDeliveryModal();
    // Only move next if in navigation mode
    if (state.isNavigating) {
        moveToNextDelivery();
    } else {
        renderDeliveryList(); // Refresh list to show "Entregado"
    }

    btn.disabled = false;
    btn.textContent = originalText;
}

// ============ UI Functions (Navigation) ============
function startNavigation() {
    state.isNavigating = true;
    state.currentDeliveryIndex = 0;

    // Show navigation panel
    document.getElementById('navPanel').classList.add('active');

    updateNavigationPanel();
}

function updateNavigationPanel() {
    // Find next non-depot, non-waypoint delivery
    const deliveries = state.optimizedRoute.filter(n => !n.is_depot && !n.is_security_waypoint);

    if (state.currentDeliveryIndex >= deliveries.length) {
        // All deliveries complete
        document.getElementById('navPanel').classList.remove('active');
        showToast('¡Todas las entregas completadas!', 'success');
        return;
    }

    const current = deliveries[state.currentDeliveryIndex];

    document.getElementById('navDestName').textContent = current.name;
    document.getElementById('navProduct').textContent = '🧀 Producto'; // Could be dynamic if we had it in optimization result
    document.getElementById('navKg').textContent = '⚖️ -- kg';
    document.getElementById('deliveryOrderId').value = current.id;

    // Pan map to current destination
    if (state.map) {
        state.map.panTo({ lat: current.lat, lng: current.lng });
        state.map.setZoom(16); // Closer zoom for nav
    }
}

function navigateToNext() {
    const deliveries = state.optimizedRoute.filter(n => !n.is_depot && !n.is_security_waypoint);

    // First check if we should go to security waypoint
    const waypoint = state.optimizedRoute.find(n => n.is_security_waypoint);
    // Logic: If we haven't visited waypoint... but we don't track that locally yet.
    // Simple logic: If index is 0, offer waypoint first? 
    // Or just let user click.

    if (state.currentDeliveryIndex < deliveries.length) {
        const current = deliveries[state.currentDeliveryIndex];
        window.open(`https://www.google.com/maps/dir/?api=1&destination=${current.lat},${current.lng}`, '_blank');
    }
}

function showDeliveryModal() {
    document.getElementById('deliveryModal').style.display = 'flex';
}

function hideDeliveryModal() {
    document.getElementById('deliveryModal').style.display = 'none';
    document.getElementById('deliveryForm').reset();
}

function moveToNextDelivery() {
    state.currentDeliveryIndex++;
    updateNavigationPanel();
}

// ============ Location Functions ============
function getCurrentLocation() {
    if (!navigator.geolocation) {
        showToast('Geolocalización no soportada', 'error');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            document.querySelector('input[name="latitud"]').value = lat.toFixed(6);
            document.querySelector('input[name="longitud"]').value = lng.toFixed(6);

            showToast('Ubicación capturada', 'success');
        },
        (error) => {
            showToast('Error obteniendo ubicación', 'error');
            console.error(error);
        }
    );
}

// ============ UI Functions ============
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = content.id === `tab-${tabName}` ? 'block' : 'none';
    });

    // Load data for specific tabs
    if (tabName === 'summary') {
        loadWeeklySummary();
    }
}

async function loadWeeklySummary() {
    const apiBase = getApiBase();
    try {
        const response = await fetch(`${apiBase}/api/weekly-summary`);
        const data = await response.json();

        const container = document.getElementById('weeklySummary');

        if (!data.summary || Object.keys(data.summary).length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div><p>No hay datos de preventa</p></div>';
            return;
        }

        let html = '<div class="delivery-list">';
        for (const [product, kg] of Object.entries(data.summary)) {
            html += `
        <div class="delivery-item">
          <div class="delivery-order">🧀</div>
          <div class="delivery-info">
            <div class="delivery-name">${product}</div>
            <div class="delivery-product">Total a comprar</div>
          </div>
          <div class="badge badge-primary">${kg.toFixed(1)} kg</div>
        </div>
      `;
        }
        html += '</div>';

        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

function createClient(event) {
    event.preventDefault();
    showToast("Función solo disponible en Mac (por ahora)", "warning");
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toasts');

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : type === 'warning' ? '⚠' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span> ${message}`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============ Render Functions ============
function renderDeliveryList() {
    const container = document.getElementById('deliveryList');
    const countBadge = document.getElementById('deliveryCount');

    if (!state.orders.length) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><p>No hay entregas para esta fecha</p></div>';
        countBadge.textContent = '0';
        return;
    }

    countBadge.textContent = state.orders.length;

    let html = '';
    state.orders.forEach((order, index) => {
        const status = order.Estatus || 'Pendiente';
        const isCompleted = status === 'Entregado';

        html += `
      <div class="delivery-item ${isCompleted ? 'completed' : ''}" onclick="focusOnDelivery(${index})">
        <div class="delivery-order">${order.Orden_Visita || index + 1}</div>
        <div class="delivery-info">
          <div class="delivery-name">${order.Nombre_Negocio || 'Cliente'}</div>
          <div class="delivery-product">
            ${order.Producto || ''}
            <span class="delivery-kg">${order.Kg_Solicitados || 0} kg</span>
          </div>
        </div>
        <span class="badge ${isCompleted ? 'badge-success' : 'badge-warning'}">${status}</span>
      </div>
    `;
    });

    container.innerHTML = html;
}

function renderOptimizedRoute() {
    const container = document.getElementById('deliveryList');
    const countBadge = document.getElementById('deliveryCount');

    if (!state.optimizedRoute.length) return;

    // Filter out depot and waypoint for count
    const deliveries = state.optimizedRoute.filter(n => !n.is_depot && !n.is_security_waypoint);
    countBadge.textContent = deliveries.length;

    let html = '';
    let visitNum = 0;

    state.optimizedRoute.forEach((node) => {
        if (node.is_depot) {
            html += `
        <div class="delivery-item" style="opacity: 0.7;">
          <div class="delivery-order" style="background: var(--text-muted);">🏠</div>
          <div class="delivery-info">
            <div class="delivery-name">${node.name}</div>
            <div class="delivery-product">Punto de origen</div>
          </div>
        </div>
      `;
        } else if (node.is_security_waypoint) {
            html += `
        <div class="delivery-item" style="border-color: var(--warning);">
          <div class="delivery-order" style="background: var(--warning);">⚠️</div>
          <div class="delivery-info">
            <div class="delivery-name">${node.name}</div>
            <div class="delivery-product">Waypoint de Seguridad</div>
          </div>
          <span class="badge badge-warning">Obligatorio</span>
        </div>
      `;
        } else {
            visitNum++;
            html += `
        <div class="delivery-item" onclick="focusOnNode('${node.id}')">
          <div class="delivery-order">${visitNum}</div>
          <div class="delivery-info">
            <div class="delivery-name">${node.name}</div>
            <div class="delivery-product">Entrega #${visitNum}</div>
          </div>
        </div>
      `;
        }
    });

    container.innerHTML = html;
}

function updateStats() {
    document.getElementById('totalDeliveries').textContent = state.orders.length;
}

// ============ Map Functions ============
function updateMapMarkers() {
    // Clear existing markers
    state.markers.forEach(m => m.setMap(null));
    state.markers = [];

    if (!state.orders.length) return;

    const bounds = new google.maps.LatLngBounds();

    state.orders.forEach((order, index) => {
        if (!order.Latitud || !order.Longitud) return;

        const position = { lat: order.Latitud, lng: order.Longitud };
        bounds.extend(position);

        const marker = new google.maps.Marker({
            position,
            map: state.map,
            label: {
                text: String(index + 1),
                color: 'white',
                fontWeight: 'bold'
            },
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 15,
                fillColor: '#6366f1',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2
            }
        });

        marker.addListener('click', () => {
            focusOnDelivery(index);
        });

        state.markers.push(marker);
    });

    if (state.orders.length > 0) {
        state.map.fitBounds(bounds);
    }
}

function drawRouteOnMap() {
    // Clear existing path
    if (state.routePath) {
        state.routePath.setMap(null);
    }

    // Clear existing markers
    state.markers.forEach(m => m.setMap(null));
    state.markers = [];

    if (!state.optimizedRoute.length) return;

    const path = [];
    const bounds = new google.maps.LatLngBounds();

    state.optimizedRoute.forEach((node, index) => {
        const position = { lat: node.lat, lng: node.lng };
        path.push(position);
        bounds.extend(position);

        let iconConfig;
        if (node.is_depot) {
            iconConfig = {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 18,
                fillColor: '#64748b',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 3
            };
        } else if (node.is_security_waypoint) {
            iconConfig = {
                path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                scale: 8,
                fillColor: '#f59e0b',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2,
                rotation: 0
            };
        } else {
            iconConfig = {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 15,
                fillColor: '#6366f1',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2
            };
        }

        const marker = new google.maps.Marker({
            position,
            map: state.map,
            label: node.is_depot ? { text: '🏠', fontSize: '16px' } : (
                node.is_security_waypoint ? { text: '⚠️', fontSize: '14px' } : {
                    text: String(node.visit_order || index),
                    color: 'white',
                    fontWeight: 'bold'
                }
            ),
            icon: iconConfig,
            zIndex: node.is_depot ? 1 : (node.is_security_waypoint ? 2 : 3)
        });

        state.markers.push(marker);
    });

    // Draw route line
    state.routePath = new google.maps.Polyline({
        path,
        geodesic: true,
        strokeColor: '#6366f1',
        strokeOpacity: 0.8,
        strokeWeight: 4
    });

    state.routePath.setMap(state.map);
    state.map.fitBounds(bounds);
}

function centerOnRoute() {
    if (state.optimizedRoute.length) {
        const bounds = new google.maps.LatLngBounds();
        state.optimizedRoute.forEach(node => {
            bounds.extend({ lat: node.lat, lng: node.lng });
        });
        state.map.fitBounds(bounds);
    } else if (state.orders.length) {
        const bounds = new google.maps.LatLngBounds();
        state.orders.forEach(order => {
            if (order.Latitud && order.Longitud) {
                bounds.extend({ lat: order.Latitud, lng: order.Longitud });
            }
        });
        state.map.fitBounds(bounds);
    }
}

function focusOnDelivery(index) {
    const order = state.orders[index];
    if (order && order.Latitud && order.Longitud) {
        state.map.panTo({ lat: order.Latitud, lng: order.Longitud });
        state.map.setZoom(15);
    }
}

function focusOnNode(nodeId) {
    const node = state.optimizedRoute.find(n => n.id === nodeId);
    if (node) {
        state.map.panTo({ lat: node.lat, lng: node.lng });
        state.map.setZoom(15);
    }
}

// PWA Install Handler
async function installPWA() {
    if (!window.deferredPrompt) {
        alert('No se puede instalar en este momento. Intenta "Instalar aplicación" desde el menú de Chrome.');
        return;
    }
    window.deferredPrompt.prompt();
    const { outcome } = await window.deferredPrompt.userChoice;
    console.log(`User response: ${outcome}`);
    window.deferredPrompt = null;
    document.getElementById('installAppBtn').style.display = 'none';
}

// ============ Initialize on Load ============
document.addEventListener('DOMContentLoaded', () => {
    console.log('Última Milla - Sistema iniciado');
});
