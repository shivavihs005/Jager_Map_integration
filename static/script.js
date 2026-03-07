document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const DEFAULT_ZOOM = 15;
    const POLLING_INTERVAL = 500; // ms
    const DEFAULT_SPEED_LIMIT = 20;

    // --- State ---
    let map;
    let tileLayer;
    let userMarker = null;
    let destinationMarker = null;
    let routePolyline = null;
    let userLocation = null;
    let destinationLocation = null;
    let currentMode = "AUTONOMOUS";
    let joyManager = null;
    let isDarkTheme = false;
    let hasZoomedToCar = false;

    // Control State
    let currentSpeed = 0;
    let currentAngle = 0;

    // --- DOM Elements ---
    const calcBtn = document.getElementById('calc-route-btn');
    const startTravelBtn = document.getElementById('start-travel-btn');
    const stopTravelBtn = document.getElementById('stop-travel-btn');
    const resetBtn = document.getElementById('reset-btn');
    const loader = document.getElementById('loader');
    const themeToggle = document.getElementById('theme-toggle');

    // Status Elements
    const motionStateEl = document.getElementById('motion-state');
    const currentModeEl = document.getElementById('current-mode');
    const gpsStatusEl = document.getElementById('gps-status');
    const hudLat = document.getElementById('hud-lat');
    const hudLng = document.getElementById('hud-lng');
    const hudSpeed = document.getElementById('hud-speed');

    // Sensor Elements - GPS
    const sGpsLat = document.getElementById('s-gps-lat');
    const sGpsLng = document.getElementById('s-gps-lng');
    const sGpsAlt = document.getElementById('s-gps-alt');
    const sGpsSats = document.getElementById('s-gps-sats');
    const sGpsDot = document.getElementById('s-gps-dot');

    // Sensor Elements - IMU
    const sAccX = document.getElementById('s-acc-x');
    const sAccY = document.getElementById('s-acc-y');
    const sAccZ = document.getElementById('s-acc-z');
    const sGyroX = document.getElementById('s-gyro-x');
    const sGyroY = document.getElementById('s-gyro-y');
    const sGyroZ = document.getElementById('s-gyro-z');
    const sTemp = document.getElementById('s-temp');
    const sImuDot = document.getElementById('s-imu-dot');

    // Sensor Elements - Magnetometer
    const sMagX = document.getElementById('s-mag-x');
    const sMagY = document.getElementById('s-mag-y');
    const sMagHdg = document.getElementById('s-mag-hdg');
    const sMagDot = document.getElementById('s-mag-dot');

    // Dual HUD Elements (Map and Manual views)
    const hudHeading = document.getElementById('hud-heading');
    const manualHudLat = document.getElementById('manual-hud-lat');
    const manualHudLng = document.getElementById('manual-hud-lng');
    const manualHudSpeed = document.getElementById('manual-hud-speed');
    const manualHudHeading = document.getElementById('manual-hud-heading');

    // Views
    const mapView = document.getElementById('map-view');
    const manualView = document.getElementById('manual-view');
    const sidebar = document.querySelector('.sidebar');

    // Controls
    const modeBtns = document.querySelectorAll('.mode-btn');
    const manualControls = document.getElementById('manual-controls');
    const semiAutoControls = document.getElementById('semi-auto-controls');
    const forwardBtn = document.getElementById('btn-forward');
    const backwardBtn = document.getElementById('btn-backward');

    // Sliders
    const maxSpeedSlider = document.getElementById('max-speed');
    const maxTurnSlider = document.getElementById('max-turn');
    const speedVal = document.getElementById('speed-val');
    const turnVal = document.getElementById('turn-val');

    // --- Initialization ---
    maxSpeedSlider.value = DEFAULT_SPEED_LIMIT;
    speedVal.textContent = DEFAULT_SPEED_LIMIT;

    initMap();
    setTimeout(initJoystick, 500);
    setupEventListeners();
    updateConfig();
    startPolling();
    locateUser();
    updateModeUI("AUTONOMOUS");

    // ── MAP SETUP ──────────────────────────────────────────────────────────────
    function initMap() {
        map = L.map('map').setView([13.08, 80.27], DEFAULT_ZOOM);

        const darkUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
        const lightUrl = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

        tileLayer = L.tileLayer(isDarkTheme ? darkUrl : lightUrl, {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        map.on('click', handleMapClick);

        themeToggle.addEventListener('change', (e) => {
            isDarkTheme = e.target.checked;
            document.body.classList.toggle('light-theme', !isDarkTheme);
            tileLayer.setUrl(isDarkTheme ? darkUrl : lightUrl);
        });
    }

    // ── JOYSTICK ───────────────────────────────────────────────────────────────
    function initJoystick() {
        if (joyManager) { joyManager.destroy(); joyManager = null; }
        const zone = document.getElementById('joystick-zone');
        if (!zone) return;
        zone.querySelectorAll('.back, .front').forEach(el => el.remove());
        if (zone.offsetWidth === 0 || zone.offsetHeight === 0) return;

        joyManager = nipplejs.create({
            zone: zone,
            mode: 'static',
            position: { left: '50%', top: '50%' },
            color: '#00f2ff',
            size: Math.min(zone.offsetWidth, zone.offsetHeight) - 10,
            lockX: true,
            restOpacity: 0.8,
            fadeTime: 0
        });

        joyManager.on('move', (evt, data) => {
            if (currentMode !== 'MANUAL') return;
            const maxDist = (Math.min(zone.offsetWidth, zone.offsetHeight) - 10) / 2;
            let val = data.instance.frontPosition.x / maxDist;
            val = Math.max(-1.0, Math.min(1.0, val));
            currentAngle = val;
            sendControl();
        });

        joyManager.on('end', () => {
            if (currentMode !== 'MANUAL') return;
            currentAngle = 0;
            sendControl();
        });
    }

    function destroyJoystick() {
        if (joyManager) { joyManager.destroy(); joyManager = null; }
    }

    // ── EVENT LISTENERS ────────────────────────────────────────────────────────
    function setupEventListeners() {
        modeBtns.forEach(btn => {
            btn.addEventListener('click', () => setMode(btn.dataset.mode));
        });

        maxSpeedSlider.addEventListener('input', (e) => {
            speedVal.textContent = e.target.value;
            updateConfig();
        });

        if (forwardBtn && backwardBtn) {
            const bindDrive = (btn, spd) => {
                btn.addEventListener('mousedown', () => { if (currentMode === 'MANUAL') { currentSpeed = spd; sendControl(); } });
                btn.addEventListener('mouseup', stopMotor);
                btn.addEventListener('mouseleave', stopMotor);
                btn.addEventListener('touchstart', (e) => { e.preventDefault(); if (currentMode === 'MANUAL') { currentSpeed = spd; sendControl(); } });
                btn.addEventListener('touchend', (e) => { e.preventDefault(); stopMotor(); });
            };
            bindDrive(forwardBtn, 100);
            bindDrive(backwardBtn, -100);
        }

        const pauseTravelBtn = document.getElementById('pause-travel-btn');
        const continueTravelBtn = document.getElementById('continue-travel-btn');
        const btnBackAuto = document.getElementById('btn-back-auto');

        calcBtn.addEventListener('click', calculateRoute);
        startTravelBtn.addEventListener('click', startTravel);
        stopTravelBtn.addEventListener('click', stopTravel);
        pauseTravelBtn.addEventListener('click', pauseTravel);
        continueTravelBtn.addEventListener('click', continueTravel);
        resetBtn.addEventListener('click', resetMap);

        if (btnBackAuto) {
            btnBackAuto.addEventListener('click', () => setMode('AUTONOMOUS'));
        }
    }

    function stopMotor() { currentSpeed = 0; sendControl(); }

    // ── API CALLS ──────────────────────────────────────────────────────────────
    function setMode(mode) {
        fetch('/api/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode })
        }).then(r => r.json()).then(d => {
            updateModeUI(mode);
        }).catch(console.error);
    }

    function sendControl() {
        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed: currentSpeed, angle: currentAngle })
        }).catch(console.error);
    }

    function updateConfig() {
        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_speed: maxSpeedSlider.value })
        });
    }

    // ── POLLING ────────────────────────────────────────────────────────────────
    function updateState() {
        // Location + vehicle state
        fetch('/api/location')
            .then(r => r.json())
            .then(loc => {
                if (mainUserUpdate(loc)) {
                    gpsStatusEl.textContent = "LOCKED";
                    gpsStatusEl.style.color = "#2ed573";
                } else {
                    gpsStatusEl.textContent = "SEARCHING";
                    gpsStatusEl.style.color = "#ffa502";
                }
            }).catch(() => { });

        fetch('/api/state')
            .then(r => r.json())
            .then(data => {
                if (motionStateEl && data.motion_state)
                    motionStateEl.textContent = data.motion_state.replace('_', ' ');
                if (data.mode && data.mode !== currentMode) updateModeUI(data.mode);
            }).catch(() => { });

        // Sensor telemetry
        fetch('/api/sensors')
            .then(r => r.json())
            .then(s => updateSensorUI(s))
            .catch(() => { });
    }

    function startPolling() {
        setInterval(updateState, POLLING_INTERVAL);
    }

    // ── SENSOR UI ──────────────────────────────────────────────────────────────
    function updateSensorUI(s) {
        // GPS
        if (s.gps) {
            const g = s.gps;
            if (sGpsLat) sGpsLat.textContent = g.fix ? g.latitude.toFixed(6) : '--';
            if (sGpsLng) sGpsLng.textContent = g.fix ? g.longitude.toFixed(6) : '--';
            if (sGpsAlt) sGpsAlt.textContent = g.fix ? g.altitude.toFixed(1) + 'm' : '--';
            if (sGpsSats) sGpsSats.textContent = g.satellites;
            if (sGpsDot) { sGpsDot.className = 'sensor-dot ' + (g.fix ? 'ok' : 'err'); }
        }

        // IMU
        if (s.imu) {
            const i = s.imu;
            const fmt = (v) => v !== undefined ? v.toFixed(2) : '--';
            if (sAccX) sAccX.textContent = fmt(i.acc_x);
            if (sAccY) sAccY.textContent = fmt(i.acc_y);
            if (sAccZ) sAccZ.textContent = fmt(i.acc_z);
            if (sGyroX) sGyroX.textContent = fmt(i.gyro_x);
            if (sGyroY) sGyroY.textContent = fmt(i.gyro_y);
            if (sGyroZ) sGyroZ.textContent = fmt(i.gyro_z);
            if (sTemp) sTemp.textContent = fmt(i.temp) + ' °C';
            if (sImuDot) sImuDot.className = 'sensor-dot ok';
        }

        // Magnetometer (and Heading HUDs)
        if (s.mag) {
            const m = s.mag;
            if (sMagX) sMagX.textContent = m.mag_x !== undefined ? m.mag_x.toFixed(1) : '--';
            if (sMagY) sMagY.textContent = m.mag_y !== undefined ? m.mag_y.toFixed(1) : '--';

            let hdgStr = '--';
            if (m.heading !== undefined) {
                hdgStr = m.heading.toFixed(1) + '° ' + (m.compass_direction || getCompassDir(m.heading));
            }
            if (sMagHdg) sMagHdg.textContent = hdgStr;
            if (hudHeading) hudHeading.textContent = hdgStr;
            if (manualHudHeading) manualHudHeading.textContent = hdgStr;

            if (sMagDot) sMagDot.className = 'sensor-dot ok';
        }
    }

    function getCompassDir(heading) {
        const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
        const idx = Math.round(((heading %= 360) < 0 ? heading + 360 : heading) / 45) % 8;
        return dirs[idx];
    }

    // ── UI LOGIC ───────────────────────────────────────────────────────────────
    function updateModeUI(mode) {
        currentMode = mode;
        if (currentModeEl) currentModeEl.textContent = mode;
        modeBtns.forEach(btn => {
            if (btn.dataset.mode === mode) btn.classList.add('active');
            else btn.classList.remove('active');
        });
        if (mode === 'MANUAL') {
            if (semiAutoControls) semiAutoControls.classList.add('hidden');
            if (mapView) mapView.classList.add('hidden');
            if (sidebar) sidebar.classList.add('hidden');
            if (manualView) manualView.classList.remove('hidden');

            currentAngle = 0;
            setTimeout(initJoystick, 200);
            setTimeout(initJoystick, 600);
        } else {
            if (manualView) manualView.classList.add('hidden');
            if (mapView) mapView.classList.remove('hidden');
            if (sidebar) sidebar.classList.remove('hidden');
            if (semiAutoControls) semiAutoControls.classList.remove('hidden');

            // Re-invalidate map size when showing it again
            setTimeout(() => { if (map) map.invalidateSize(); }, 200);

            destroyJoystick();
        }
    }

    // ── MAP LOGIC ──────────────────────────────────────────────────────────────
    function locateUser() {
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(pos => {
                map.setView([pos.coords.latitude, pos.coords.longitude], DEFAULT_ZOOM);
            });
        }
    }

    function mainUserUpdate(loc) {
        if (loc.lat === 0 && loc.lng === 0) return false;
        userLocation = loc;
        if (hudLat) hudLat.textContent = loc.lat.toFixed(6);
        if (hudLng) hudLng.textContent = loc.lng.toFixed(6);
        if (manualHudLat) manualHudLat.textContent = loc.lat.toFixed(6);
        if (manualHudLng) manualHudLng.textContent = loc.lng.toFixed(6);

        if (loc.speed !== undefined) {
            const spdStr = `${loc.speed.toFixed(1)} <small>km/h</small>`;
            if (hudSpeed) hudSpeed.innerHTML = spdStr;
            if (manualHudSpeed) manualHudSpeed.innerHTML = spdStr;
        }
        if (!userMarker) {
            userMarker = L.marker([loc.lat, loc.lng], {
                icon: L.divIcon({ className: 'car-icon', html: '🚗', iconSize: [30, 30] })
            }).addTo(map).bindPopup("JAGER");
            map.setView([loc.lat, loc.lng], DEFAULT_ZOOM);
            hasZoomedToCar = true;
        } else {
            userMarker.setLatLng([loc.lat, loc.lng]);
            if (!hasZoomedToCar) { map.setView([loc.lat, loc.lng], DEFAULT_ZOOM); hasZoomedToCar = true; }
        }
        return true;
    }

    function handleMapClick(e) {
        if (currentMode !== 'AUTONOMOUS') return;
        if (destinationMarker) map.removeLayer(destinationMarker);
        destinationLocation = e.latlng;
        destinationMarker = L.marker(e.latlng, {
            icon: L.divIcon({
                className: 'dest-icon',
                html: '<div style="font-size:24px;color:#ff4757;text-shadow:0 0 5px black;">📍</div>',
                iconSize: [30, 30], iconAnchor: [15, 30], popupAnchor: [0, -30]
            })
        }).addTo(map).bindPopup("Destination").openPopup();
        calcBtn.disabled = false;
        if (routePolyline) { map.removeLayer(routePolyline); routePolyline = null; }
        startTravelBtn.classList.add('hidden');
    }

    function calculateRoute() {
        if (!userLocation || !destinationLocation) { alert("No location or destination set!"); return; }
        loader.classList.remove('hidden');
        const start = `${userLocation.lng},${userLocation.lat}`;
        const end = `${destinationLocation.lng},${destinationLocation.lat}`;
        fetch(`https://router.project-osrm.org/route/v1/driving/${start};${end}?overview=full&geometries=geojson`)
            .then(r => r.json())
            .then(data => {
                loader.classList.add('hidden');
                if (data.routes && data.routes.length > 0) {
                    drawRoute(data.routes[0].geometry);
                    startTravelBtn.classList.remove('hidden');
                } else { alert("No route found!"); }
            })
            .catch(err => { loader.classList.add('hidden'); console.error(err); alert("Routing failed."); });
    }

    let currentRouteGeoJSON = null;

    function drawRoute(geojson) {
        if (routePolyline) map.removeLayer(routePolyline);
        currentRouteGeoJSON = geojson;
        const latlngs = geojson.coordinates.map(c => [c[1], c[0]]);
        routePolyline = L.polyline(latlngs, { color: '#00f2ff', weight: 5, opacity: 0.7 }).addTo(map);
        map.fitBounds(routePolyline.getBounds());
    }

    function startTravel() {
        if (!destinationLocation || !currentRouteGeoJSON) { alert("No route to follow!"); return; }
        const waypoints = currentRouteGeoJSON.coordinates.map(c => ({ lat: c[1], lng: c[0] }));
        fetch('/api/navigate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ waypoints: waypoints })
        }).then(r => r.json()).then(d => {
            document.getElementById('start-travel-btn').classList.add('hidden');
            document.getElementById('calc-route-btn').disabled = true;
            document.getElementById('pause-travel-btn').classList.remove('hidden');
            document.getElementById('stop-travel-btn').classList.remove('hidden');
        });
    }

    function pauseTravel() {
        fetch('/api/pause', { method: 'POST' }).then(() => {
            document.getElementById('pause-travel-btn').classList.add('hidden');
            document.getElementById('continue-travel-btn').classList.remove('hidden');
        });
    }

    function continueTravel() {
        fetch('/api/continue', { method: 'POST' }).then(() => {
            document.getElementById('continue-travel-btn').classList.add('hidden');
            document.getElementById('pause-travel-btn').classList.remove('hidden');
        });
    }

    function stopTravel() {
        fetch('/api/stop', { method: 'POST' })
            .then(() => {
                document.getElementById('stop-travel-btn').classList.add('hidden');
                document.getElementById('pause-travel-btn').classList.add('hidden');
                document.getElementById('continue-travel-btn').classList.add('hidden');
                document.getElementById('start-travel-btn').classList.remove('hidden');
            });
    }

    function resetMap() {
        if (destinationMarker) map.removeLayer(destinationMarker);
        if (routePolyline) map.removeLayer(routePolyline);
        destinationMarker = null; destinationLocation = null;
        currentRouteGeoJSON = null;

        calcBtn.disabled = true;
        document.getElementById('start-travel-btn').classList.add('hidden');
        document.getElementById('stop-travel-btn').classList.add('hidden');
        document.getElementById('pause-travel-btn').classList.add('hidden');
        document.getElementById('continue-travel-btn').classList.add('hidden');

        // Stop any active mission
        fetch('/api/stop', { method: 'POST' });
    }
});
