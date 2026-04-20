let map;
let joystickAccel;
let joystickSteer;
let updateInterval;
let maxSpeed = 50;
let currentLat = 37.7749; // Default placeholder
let currentLon = -122.4194;
let destinationMarker = null;
let routeLine = null;
let junctionMarkers = [];
let globalPathCoordinates = null;
let isSystemActive = false;
let carMarker = null;

// Basic 1D Kalman Filter for GPS Smoothing
class KalmanFilter {
    constructor(R, Q) {
        this.R = R; // Measurement Noise
        this.Q = Q; // Process Noise
        this.P = 1; // Error covariance
        this.X = 0; // Estimated Signal
        this.K = 0; // Kalman Gain
        this.initialized = false;
    }
    filter(measurement) {
        if (!this.initialized) {
            this.X = measurement;
            this.initialized = true;
            return this.X;
        }
        // Predict
        this.P = this.P + this.Q;
        // Update
        this.K = this.P / (this.P + this.R);
        this.X = this.X + this.K * (measurement - this.X);
        this.P = (1 - this.K) * this.P;
        return this.X;
    }
}
const kfLat = new KalmanFilter(0.001, 0.00001);
const kfLon = new KalmanFilter(0.001, 0.00001);

function updateSpeed(val) {
    maxSpeed = parseInt(val);
    if (document.getElementById('speed-val-out')) document.getElementById('speed-val-out').innerText = val;
    if (document.getElementById('speed-val-in')) document.getElementById('speed-val-in').innerText = val;
    if (document.getElementById('speed-val-man')) document.getElementById('speed-val-man').innerText = val;
    
    fetch('/api/speed', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ speed: maxSpeed })
    }).catch(err => console.warn('Speed API err:', err));
}

// View switching logic
function switchView(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    
    clearInterval(updateInterval);
    
    if (viewId === 'map-view' || viewId === 'outdoor-view') {
        initMap();
        startTelemetryLoop();
    } else if (viewId === 'manual-view') {
        initJoystick();
        startTelemetryLoop();
        fetch('/api/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ mode: 'MANUAL' })
        }).catch(err => console.warn('Mode API err:', err));
    } else if (viewId === 'indoor-view') {
        startTelemetryLoop();
    } else if (viewId === 'home-view') {
        // Stop everything when going back home
        fetch('/api/stop', { method: 'POST' }).catch(() => {});
    }
}

// Leaflet Map Initialization
function initMap() {
    if (!map) {
        map = L.map('map-container').setView([currentLat, currentLon], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // Click to set destination
        map.on('click', function(e) {
            if (destinationMarker) map.removeLayer(destinationMarker);
            destinationMarker = L.marker(e.latlng).addTo(map);
            console.log("Destination set to:", e.latlng.lat, e.latlng.lng);
        });

    } else {
        setTimeout(() => map.invalidateSize(), 100);
    }
}

// Joystick Initialization (nipplejs)
function initJoystick() {
    if (joystickAccel) joystickAccel.destroy();
    if (joystickSteer) joystickSteer.destroy();
    
    // Vertical Lock for Acceleration
    joystickAccel = nipplejs.create({
        zone: document.getElementById('joystick-accel'),
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: '#00f0ff',
        size: 200,
        lockX: false,
        lockY: true
    });

    // Horizontal Lock for Steering
    joystickSteer = nipplejs.create({
        zone: document.getElementById('joystick-steer'),
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: '#00ff9f',
        size: 200,
        lockX: true,
        lockY: false
    });

    let currentAccel = 0;
    let currentSteer = 0;

    joystickAccel.on('move', function (evt, data) {
        const distance = data.distance; 
        const angle = data.angle.radian;
        currentAccel = Math.sin(angle) * distance; 
        sendDualJoystickData(currentAccel, currentSteer);
    });
    joystickAccel.on('end', function () {
        currentAccel = 0;
        sendDualJoystickData(0, currentSteer);
        setTimeout(function() { sendDualJoystickData(0, currentSteer); }, 50);
        setTimeout(function() { sendDualJoystickData(0, currentSteer); }, 150);
    });

    joystickSteer.on('move', function (evt, data) {
        const distance = data.distance; 
        const angle = data.angle.radian;
        currentSteer = Math.cos(angle) * distance; 
        sendDualJoystickData(currentAccel, currentSteer);
    });
    joystickSteer.on('end', function () {
        currentSteer = 0;
        sendDualJoystickData(currentAccel, 0);
        setTimeout(function() { sendDualJoystickData(currentAccel, 0); }, 50);
        setTimeout(function() { sendDualJoystickData(currentAccel, 0); }, 150);
    });
}

function sendDualJoystickData(accel, steer) {
    // accel: -100 (reverse) to +100 (forward), steer: -100 (left) to +100 (right)
    const y = Math.round(accel);
    const x = Math.round(steer);
    
    fetch('/api/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ x: x, y: y })
    }).catch(err => console.warn('Joystick API err:', err));
}

// API Controls
function startSystem(mode) {
    if (mode === 'OUTDOOR') {
        isSystemActive = true;
        logToTerminal('out-term', 'INITIATING SYSTEM ENGAGEMENT...', 'info');
        
        if (globalPathCoordinates && globalPathCoordinates.length > 1) {
            let p1 = globalPathCoordinates[0]; // [lon, lat]
            let p2 = globalPathCoordinates[1];
            
            // Helper to get true geographical bearing
            function getBearing(lat1, lon1, lat2, lon2) {
                const toRad = Math.PI / 180;
                const toDeg = 180 / Math.PI;
                const dLon = (lon2 - lon1) * toRad;
                lat1 = lat1 * toRad;
                lat2 = lat2 * toRad;
                const y = Math.sin(dLon) * Math.cos(lat2);
                const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
                let brng = Math.atan2(y, x) * toDeg;
                return (brng + 360) % 360;
            }
            
            const brng = getBearing(p1[1], p1[0], p2[1], p2[0]);
            
            logToTerminal('out-term', `[TRAVEL MODE] Aligned camera to heading ${Math.round(brng)}°`, 'success');
            
            // Zoom deeply into the start position
            map.flyTo([p1[1], p1[0]], 19, { animate: true, duration: 1.5 });
            
            setTimeout(() => {
                // Rotate the map container directly via CSS, scaled slightly to hide clipped corners
                const mapContainer = document.getElementById('map-container');
                if (mapContainer) mapContainer.style.transform = `scale(1.6) rotate(${-brng}deg)`;
                
                // Align visual HUD Compass to real True North relative to map
                const compass = document.getElementById('compass-icon');
                if (compass) compass.style.transform = `rotate(${-brng}deg)`;
                
                // Disable map interaction during Travel Mode.
                map.dragging.disable();
                map.touchZoom.disable();
                map.scrollWheelZoom.disable();
                map.doubleClickZoom.disable();
                map.boxZoom.disable();
                
                logToTerminal('out-term', `VEHICLE IN MOTION. CAMERA LOCKED TO TRACKING.`, 'info');
            }, 1000); 
            
        } else {
             logToTerminal('out-term', 'SYSTEM BLOCK: NO PATH CALCULATED.', 'error');
             return;
        }
    } 
    
    if (mode === 'INDOOR') {
        logToTerminal('in-term', 'INITIATING INDOOR AUTONOMOUS MODE...', 'info');
        logToTerminal('in-term', 'Ultrasonic sensor active. Ramping speed...', 'info');
    }

    // Execute backend sequence
    fetch('/api/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ mode: mode })
    }).then(res => res.json())
      .then(data => console.log('Backend Start:', data));
}

function stopSystem() {
    fetch('/api/stop', { method: 'POST' });
    console.log("API [STOP/RESET] executed");
    isSystemActive = false;
    
    // Reset rotations
    const mapContainer = document.getElementById('map-container');
    const compass = document.getElementById('compass-icon');
    if (mapContainer) mapContainer.style.transform = `scale(1) rotate(0deg)`;
    if (compass) compass.style.transform = `rotate(0deg)`;
    
    // RESTORE map interaction inputs
    if (map) {
        map.dragging.enable();
        map.touchZoom.enable();
        map.scrollWheelZoom.enable();
        map.doubleClickZoom.enable();
        map.boxZoom.enable();
    }
    
    // Standardize map back
    if (map && currentLat && currentLon) {
        map.flyTo([currentLat, currentLon], 15, { animate: true, duration: 1 });
    }
    
    // Clear path
    if (routeLine) {
        map.removeLayer(routeLine);
        routeLine = null;
    }
    if (map) {
        junctionMarkers.forEach(m => map.removeLayer(m));
    }
    junctionMarkers = [];
    globalPathCoordinates = null;
    
    if (map && destinationMarker) {
        map.removeLayer(destinationMarker);
        destinationMarker = null;
    }
    
    const activeTerm = document.getElementById('outdoor-view').classList.contains('active') ? 'out-term' : 
                       (document.getElementById('indoor-view').classList.contains('active') ? 'in-term' : null);
    if(activeTerm) logToTerminal(activeTerm, 'SYSTEM HALTED. HARDWARE RESET TO NEUTRAL.', 'warn');
}

// Telemetry Polling
function startTelemetryLoop() {
    if (updateInterval) clearInterval(updateInterval);
    updateInterval = setInterval(() => {
        fetch('/api/sensors')
            .then(res => res.json())
            .then(data => {
                const gps = data.gps;
                const motor_speed = data.motor_speed || 0;
                const distance_cm = data.distance_cm || 0;
                const motor_state = data.motor_state || 'STOP';
                const heading = data.heading || 0;
                const steering = data.steering_angle || 1040;

                if (gps && gps.locked) {
                    // Update Map Marker via Kalman 
                    const rawLat = gps.lat;
                    const rawLon = gps.lon;
                    currentLat = kfLat.filter(rawLat);
                    currentLon = kfLon.filter(rawLon);
                    
                    if (map) {
                        if (!carMarker) {
                            const carIcon = L.divIcon({
                                html: '<div style="font-size: 28px; text-shadow: 0 0 10px var(--neon-blue); line-height: 1;">🚙</div>',
                                className: 'car-marker',
                                iconSize: [28, 28],
                                iconAnchor: [14, 14]
                            });
                            carMarker = L.marker([currentLat, currentLon], {icon: carIcon, zIndexOffset: 1000})
                                         .addTo(map);
                            map.setView([currentLat, currentLon], 15);
                        } else {
                            carMarker.setLatLng([currentLat, currentLon]);
                            if (isSystemActive) {
                                map.panTo([currentLat, currentLon], { animate: true, duration: 0.5 });
                            }
                        }
                    }
                }

                // ========== OUTDOOR VIEW ==========
                if(document.getElementById('gps-status')) {
                    document.getElementById('gps-status').innerText = (gps && gps.locked) ? "LOCKED" : "NO FIX";
                    document.getElementById('out-speed').innerText = motor_speed;
                    document.getElementById('out-dist').innerText = distance_cm;
                    document.getElementById('out-heading').innerText = Math.round(heading);
                }
                
                // ========== INDOOR VIEW ==========
                if(document.getElementById('indoor-dist')) {
                    document.getElementById('indoor-dist').innerText = distance_cm + "cm";
                    document.getElementById('indoor-state').innerText = motor_state;
                    document.getElementById('indoor-speed').innerText = motor_speed;
                    document.getElementById('indoor-heading').innerText = Math.round(heading);
                    
                    if (distance_cm < 15) {
                         document.getElementById('indoor-dist').style.color = '#ff003c';
                    } else if (distance_cm < 40) {
                         document.getElementById('indoor-dist').style.color = '#ffeb3b';
                    } else {
                         document.getElementById('indoor-dist').style.color = '#00ff9f';
                    }
                }
                
                // ========== INDOOR SONAR VISUALIZATION ==========
                updateSonarViz(distance_cm);

                // ========== MANUAL VIEW ==========
                if(document.getElementById('man-state')) {
                    document.getElementById('man-state').innerText = motor_state;
                    document.getElementById('man-dist').innerText = distance_cm;
                    document.getElementById('man-heading').innerText = Math.round(heading);
                    document.getElementById('man-speed').innerText = motor_speed;
                }

                // Terminal logging (throttled)
                if (Math.random() > 0.8) {
                    const activeTerm = document.getElementById('outdoor-view').classList.contains('active') ? 'out-term' : 
                                       (document.getElementById('indoor-view').classList.contains('active') ? 'in-term' : null);
                    if (activeTerm && gps && gps.locked) {
                        logToTerminal(activeTerm, `POS: ${currentLat.toFixed(5)},${currentLon.toFixed(5)} | STATE: ${motor_state} | SPD: ${motor_speed}% | HDG: ${Math.round(heading)}°`);
                    }
                }
            })
            .catch(err => console.error("Telemetry fetch error", err));
    }, 500); // 2Hz updates
}

// ========== SONAR DISTANCE VISUALIZATION ==========
function updateSonarViz(distanceCm) {
    const valEl = document.getElementById('sonar-distance-val');
    const barEl = document.getElementById('sonar-bar-fill');
    const statusEl = document.getElementById('sonar-status-label');
    
    if (!valEl || !barEl || !statusEl) return;
    
    valEl.innerText = Math.round(distanceCm);
    
    // Bar fill: 0-150cm range, clamp at 100%
    const pct = Math.min(100, (distanceCm / 150) * 100);
    barEl.style.width = pct + '%';
    
    // Color coding
    if (distanceCm < 15) {
        barEl.style.background = 'linear-gradient(90deg, #ff003c, #ff4466)';
        barEl.style.boxShadow = '0 0 15px rgba(255, 0, 60, 0.8)';
        statusEl.innerText = '⚠ DANGER — OBSTACLE';
        statusEl.style.color = '#ff003c';
        valEl.style.color = '#ff003c';
    } else if (distanceCm < 40) {
        barEl.style.background = 'linear-gradient(90deg, #ffeb3b, #ff9800)';
        barEl.style.boxShadow = '0 0 10px rgba(255, 235, 59, 0.6)';
        statusEl.innerText = '⚡ CAUTION';
        statusEl.style.color = '#ffeb3b';
        valEl.style.color = '#ffeb3b';
    } else {
        barEl.style.background = 'linear-gradient(90deg, #00ff9f, #00f0ff)';
        barEl.style.boxShadow = '0 0 10px rgba(0, 255, 159, 0.6)';
        statusEl.innerText = '✓ CLEAR PATH';
        statusEl.style.color = '#00ff9f';
        valEl.style.color = '#00ff9f';
    }
}

// Terminal Logging System
function logToTerminal(termId, msg, type = 'normal') {
    const term = document.getElementById(termId);
    if (!term) return;
    
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                    now.getMinutes().toString().padStart(2, '0') + ':' + 
                    now.getSeconds().toString().padStart(2, '0');
    
    let colorClass = '';
    if (type === 'error') colorClass = 'log-error';
    if (type === 'warn') colorClass = 'log-warn';
    if (type === 'info') colorClass = 'log-info';

    const logEl = document.createElement('div');
    logEl.className = 'terminal-log';
    logEl.innerHTML = `<span class="log-timestamp">[${timeStr}]</span><span class="${colorClass}">${msg}</span>`;
    
    term.appendChild(logEl);
    
    // Keep max 50 lines to prevent lag
    if (term.childNodes.length > 50) term.removeChild(term.firstChild);
    
    // Scroll to bottom
    term.scrollTop = term.scrollHeight;
}

// Sensor Calibration
function calibrateSensors(termId) {
    logToTerminal(termId, "REQUESTING HARDWARE DIAGNOSTICS FROM PI...", "warn");
    
    fetch('/api/calibrate')
        .then(res => res.json())
        .then(data => {
            if (data.status === "success" && data.tests) {
                let delay = 500;
                for (const [component, status] of Object.entries(data.tests)) {
                    setTimeout(() => {
                        logToTerminal(termId, `[DIAG] ${component}: ${status}`, status.includes("PASS") ? "info" : "error");
                    }, delay);
                    delay += 600;
                }
                setTimeout(() => logToTerminal(termId, "CALIBRATION SEQUENCE COMPLETE.", "success"), delay + 200);
            }
        })
        .catch(err => {
            logToTerminal(termId, "DIAGNOSTIC NETWORK FAILURE.", "error");
        });
}

// Map Theme Toggle
function toggleMapMode() {
    const mapContainer = document.getElementById('map-container');
    const btn = document.getElementById('btn-map-theme');
    
    if (mapContainer.classList.contains('dark-mode')) {
        mapContainer.classList.remove('dark-mode');
        btn.innerText = "MAP: WHITE MODE";
        btn.classList.replace('neon-purple', 'neon-blue');
    } else {
        mapContainer.classList.add('dark-mode');
        btn.innerText = "MAP: DARK MODE";
        btn.classList.replace('neon-blue', 'neon-purple');
    }
}

// OSRM Path Routing
function calculatePath() {
    if (!destinationMarker) {
        alert("Please click on the map to set a destination pin first!");
        return;
    }
    
    logToTerminal('out-term', 'REQUESTING ROUTE FROM OSRM...', 'warn');
    
    const destLat = destinationMarker.getLatLng().lat;
    const destLon = destinationMarker.getLatLng().lng;
    
    // OSRM expects: lon,lat;lon,lat. We add &steps=true to get maneuver locations
    const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${currentLon},${currentLat};${destLon},${destLat}?overview=full&geometries=geojson&steps=true`;

    fetch(osrmUrl)
        .then(res => res.json())
        .then(data => {
            if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
                const route = data.routes[0];
                const coordinates = route.geometry.coordinates;
                globalPathCoordinates = coordinates;
                
                // OSRM returns GeoJSON [lon, lat], Leaflet polyline expects [lat, lon]
                const latLngs = coordinates.map(coord => [coord[1], coord[0]]);
                
                if (routeLine) {
                    map.removeLayer(routeLine);
                }
                
                routeLine = L.polyline(latLngs, {
                    color: '#00f0ff', // neon blue
                    weight: 4, 
                    opacity: 0.8, 
                    dashArray: '10, 10'
                }).addTo(map);
                
                map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
                
                // Parse and draw junctions/waypoints based on geometric turns
                junctionMarkers.forEach(m => map.removeLayer(m));
                junctionMarkers = [];
                let waypointCount = 0;
                
                // Helper to calculate angle between three points
                function getAngle(p1, p2, p3) {
                    const dx1 = p2[0] - p1[0];
                    const dy1 = p2[1] - p1[1];
                    const dx2 = p3[0] - p2[0];
                    const dy2 = p3[1] - p2[1];
                    const a1 = Math.atan2(dy1, dx1);
                    const a2 = Math.atan2(dy2, dx2);
                    let diff = Math.abs((a2 - a1) * (180 / Math.PI));
                    if (diff > 180) diff = 360 - diff;
                    return diff;
                }
                
                // Helper to calculate raw line distance (Haversine in km)
                function getLineDistance(lon1, lat1, lon2, lat2) {
                    const R = 6371; // Earth's radius in km
                    const dLat = (lat2 - lat1) * Math.PI / 180;
                    const dLon = (lon2 - lon1) * Math.PI / 180;
                    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                              Math.sin(dLon/2) * Math.sin(dLon/2);
                    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                    return R * c;
                }
                
                // Helper to get Left/Right turn direction using 2D cross product
                function getTurnDirection(p1, p2, p3) {
                    const dx1 = p2[0] - p1[0];
                    const dy1 = p2[1] - p1[1];
                    const dx2 = p3[0] - p2[0];
                    const dy2 = p3[1] - p2[1];
                    const cp = dx1 * dy2 - dy1 * dx2;
                    return cp > 0 ? "Left" : "Right";
                }
                
                // Helper to format exact distances
                function formatDist(distKm) {
                    if (distKm < 1) {
                        return Math.round(distKm * 1000) + " meters";
                    }
                    const km = Math.floor(distKm);
                    const m = Math.round((distKm - km) * 1000);
                    return m > 0 ? `${km} km and ${m} meters` : `${km} km`;
                }

                let computedDistanceKm = 0;
                let segmentDistAccum = 0;

                // Create waypoints at the start, any turning point (>5 degrees), and the end
                for (let i = 0; i < coordinates.length; i++) {
                    // Distance accumulation
                    if (i > 0) {
                        const d = getLineDistance(
                            coordinates[i-1][0], coordinates[i-1][1], 
                            coordinates[i][0], coordinates[i][1]
                        );
                        computedDistanceKm += d;
                        segmentDistAccum += d;
                    }
                    
                    let isWaypoint = false;
                    let angleStr = "";
                    let turnDir = "";
                    
                    if (i === 0) {
                        isWaypoint = true;
                        angleStr = "Start Point";
                        logToTerminal('out-term', `[ROUTE] Starting from current location...`, 'info');
                    } else if (i === coordinates.length - 1) {
                        isWaypoint = true;
                        angleStr = "End Point";
                        logToTerminal('out-term', `[ROUTE] Head straight for ${formatDist(segmentDistAccum)}, ARRIVING AT DESTINATION.`, 'success');
                    } else {
                        const angle = getAngle(coordinates[i-1], coordinates[i], coordinates[i+1]);
                        if (angle > 5) { // 5 degree threshold catches any curve/turn
                            isWaypoint = true;
                            turnDir = getTurnDirection(coordinates[i-1], coordinates[i], coordinates[i+1]);
                            angleStr = `Turn ${turnDir}`;
                            
                            logToTerminal('out-term', `[ROUTE] Continue for ${formatDist(segmentDistAccum)}, then TURN ${turnDir.toUpperCase()}`, 'normal');
                            segmentDistAccum = 0; // Reset step distance
                        }
                    }
                    
                    if (isWaypoint) {
                        const loc = coordinates[i]; // [lon, lat]
                        const circle = L.circleMarker([loc[1], loc[0]], {
                            color: '#ff003c', // neon red
                            fillColor: '#0a0a0a',
                            weight: 2,
                            fillOpacity: 1,
                            radius: 5
                        }).addTo(map);
                        
                        circle.bindPopup(`<b>WP ${waypointCount + 1}</b><br>${angleStr}`);
                        junctionMarkers.push(circle);
                        waypointCount++;
                    }
                }
                
                const distKm = computedDistanceKm.toFixed(2);
                logToTerminal('out-term', `PATH DRAWN: Computed Distance ${distKm} km | ${waypointCount} WAYPOINTS`, 'info');
                
                if(document.getElementById('out-wp')) {
                    document.getElementById('out-wp').innerText = `${destLat.toFixed(4)}, ${destLon.toFixed(4)}`;
                }
            } else {
                 logToTerminal('out-term', 'OSRM ROUTE FAILED: NO PATH', 'error');
            }
        })
        .catch(err => {
            console.error(err);
            logToTerminal('out-term', 'OSRM API FETCH ERROR', 'error');
        });
}
