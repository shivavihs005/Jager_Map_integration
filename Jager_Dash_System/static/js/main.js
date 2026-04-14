let map;
let joystick;
let updateInterval;

// View switching logic
function switchView(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    
    // Reset specific contexts
    clearInterval(updateInterval);
    
    if (viewId === 'map-view' || viewId === 'outdoor-view') {
        initMap();
        startTelemetryLoop();
    } else if (viewId === 'manual-view') {
        initJoystick();
        startTelemetryLoop();
        // Set mode via API
        fetch('/api/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: 'MANUAL'})
        });
    } else if (viewId === 'indoor-view') {
        startTelemetryLoop();
    }
}

// Leaflet Map Initialization
function initMap() {
    if (!map) {
        // Initial coordinates (San Francisco placeholder)
        map = L.map('map-container').setView([37.7749, -122.4194], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        let marker = null;
        // Click to set destination
        map.on('click', function(e) {
            if (marker) map.removeLayer(marker);
            marker = L.marker(e.latlng).addTo(map);
            console.log("Destination set to:", e.latlng.lat, e.latlng.lng);
            // In a real scenario, this would trigger path calculation
        });
    } else {
        setTimeout(() => map.invalidateSize(), 100);
    }
}

// Joystick Initialization (nipplejs)
function initJoystick() {
    const zone = document.getElementById('joystick-zone');
    if (joystick) {
        joystick.destroy();
    }
    
    joystick = nipplejs.create({
        zone: zone,
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: '#9f00ff',
        size: 200
    });

    joystick.on('move', function (evt, data) {
        // Compute x and y from -100 to 100
        const distance = data.distance; // max is 100
        const angle = data.angle.radian;
        
        // y is forward/backward
        const y = Math.sin(angle) * distance;
        // x is left/right
        const x = Math.cos(angle) * distance;
        
        sendJoystickData(x, y);
    });

    joystick.on('end', function () {
        sendJoystickData(0, 0);
    });
}

function sendJoystickData(x, y) {
    fetch('/api/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ x: x, y: y })
    }).catch(e => console.error("Joystick Error", e));
}

// API Controls
function startSystem(mode) {
    fetch('/api/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: mode})
    })
    .then(r => r.json())
    .then(data => console.log(data));
}

function stopSystem() {
    fetch('/api/stop', {
        method: 'POST'
    })
    .then(r => r.json())
    .then(data => console.log(data));
}

// Telemetry Polling
function startTelemetryLoop() {
    updateInterval = setInterval(() => {
        fetch('/api/sensors')
            .then(res => res.json())
            .then(data => {
                // Update generic fields
                if(document.getElementById('gps-status')) {
                    document.getElementById('gps-status').innerText = data.gps.locked ? "LOCKED" : "NO FIX";
                    document.getElementById('out-speed').innerText = data.motor_speed;
                    document.getElementById('out-dist').innerText = data.distance_cm;
                }
                
                if(document.getElementById('indoor-dist')) {
                    document.getElementById('indoor-dist').innerText = data.distance_cm + "cm";
                    document.getElementById('indoor-state').innerText = data.motor_state;
                    
                    if (data.distance_cm < 40) {
                         document.getElementById('indoor-dist').style.color = '#ff003c';
                    } else {
                         document.getElementById('indoor-dist').style.color = '#00ff9f';
                    }
                }
                
                if(document.getElementById('man-state')) {
                    document.getElementById('man-state').innerText = data.motor_state;
                    document.getElementById('man-dist').innerText = data.distance_cm;
                }
            })
            .catch(e => console.error("Telemetry Error", e));
    }, 500); // 2Hz updates
}
