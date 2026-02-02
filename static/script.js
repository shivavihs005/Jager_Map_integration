document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const DEFAULT_ZOOM = 13;
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

    let hasZooomedToCar = false;

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

    // Set Default Limit Logic
    maxSpeedSlider.value = DEFAULT_SPEED_LIMIT;
    speedVal.textContent = DEFAULT_SPEED_LIMIT;

    // Default Turn
    const DEFAULT_TURN_LIMIT = 50;
    maxTurnSlider.value = DEFAULT_TURN_LIMIT;
    turnVal.textContent = DEFAULT_TURN_LIMIT;

    initMap();
    // Delay Joystick init to ensure layout is stable
    setTimeout(initJoystick, 500);
    setupEventListeners();
    updateConfig(); // Sync initial slider
    startPolling();
    locateUser();

    // Set initial UI for mode
    updateModeUI("AUTONOMOUS");

    function initMap() {
        map = L.map('map').setView([20.5937, 78.9629], 5);

        // Map Tile Providers
        const darkUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
        // Switched to CartoDB Positron for cleaner look and better reliability
        const lightUrl = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

        // Init with Light Theme (since isDarkTheme = false now)
        tileLayer = L.tileLayer(isDarkTheme ? darkUrl : lightUrl, {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        map.on('click', handleMapClick);

        // Theme Toggle Logic
        themeToggle.addEventListener('change', (e) => {
            isDarkTheme = e.target.checked;
            document.body.classList.toggle('light-theme', !isDarkTheme);

            // Switch Map Tiles
            tileLayer.setUrl(isDarkTheme ? darkUrl : lightUrl);
        });
    }

    function initJoystick() {
        if (joyManager) return; // Already initialized

        const zone = document.getElementById('joystick-zone');
        joyManager = nipplejs.create({
            zone: zone,
            mode: 'static',
            position: { left: '50%', top: '50%' },
            color: '#00f2ff',
            size: 100, // Smaller for steer only
            lockX: true // Only allow X movement
        });

        joyManager.on('move', (evt, data) => {
            if (currentMode !== 'MANUAL') return;

            // Use frontPosition for reliable X axis value with lockX
            // data.instance.frontPosition.x is relative to center
            // Range is roughly -50 to 50 for size 100
            const maxDist = 50.0;
            let val = data.instance.frontPosition.x / maxDist;

            // Clamp
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
        if (joyManager) {
            joyManager.destroy();
            joyManager = null;
        }
    }

    function setupEventListeners() {
        // Mode Switching
        modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const newMode = btn.dataset.mode;
                setMode(newMode);
            });
        });

        // Sliders
        maxSpeedSlider.addEventListener('input', (e) => {
            speedVal.textContent = e.target.value;
            updateConfig();
        });

        maxTurnSlider.addEventListener('input', (e) => {
            turnVal.textContent = e.target.value;
            updateConfig();
        });

        // Drive Buttons (Hold to drive)
        if (forwardBtn && backwardBtn) {
            forwardBtn.addEventListener('mousedown', () => {
                if (currentMode === 'MANUAL') {
                    currentSpeed = 100; // Will be scaled by backend max_speed
                    sendControl();
                }
            });
            forwardBtn.addEventListener('mouseup', () => stopMotor());
            forwardBtn.addEventListener('mouseleave', () => stopMotor());

            // Touch support for mobile
            forwardBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (currentMode === 'MANUAL') {
                    currentSpeed = 100;
                    sendControl();
                }
            });
            forwardBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                stopMotor();
            });

            backwardBtn.addEventListener('mousedown', () => {
                if (currentMode === 'MANUAL') {
                    currentSpeed = -100;
                    sendControl();
                }
            });
            backwardBtn.addEventListener('mouseup', () => stopMotor());
            backwardBtn.addEventListener('mouseleave', () => stopMotor());

            backwardBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                if (currentMode === 'MANUAL') {
                    currentSpeed = -100;
                    sendControl();
                }
            });
            backwardBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                stopMotor();
            });
        }


        // Map Actions
        calcBtn.addEventListener('click', calculateRoute);
        startTravelBtn.addEventListener('click', startTravel);
        stopTravelBtn.addEventListener('click', stopTravel);
        resetBtn.addEventListener('click', resetMap);
    }

    function stopMotor() {
        currentSpeed = 0;
        sendControl();
    }

    // --- API Calls ---

    function setMode(mode) {
        fetch('/api/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    updateModeUI(mode);
                } else {
                    alert('Failed to switch mode: ' + data.message);
                }
            })
            .catch(err => console.error('Error setting mode:', err));
    }

    function sendControl() {
        // Send composite state
        fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed: currentSpeed, angle: currentAngle })
        }).catch(err => console.error(err));
    }

    function updateConfig() {
        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                max_speed: maxSpeedSlider.value,
                max_turn: maxTurnSlider.value
            })
        });
    }

    function updateState() {
        fetch('/api/state')
            .then(res => res.json())
            .then(data => {
                motionStateEl.textContent = data.motion_state.replace('_', ' ');

                if (data.mode !== currentMode) {
                    updateModeUI(data.mode);
                }
            })
            .catch(console.error);

        fetch('/api/location')
            .then(res => res.json())
            .then(loc => {
                if (mainUserUpdate(loc)) {
                    gpsStatusEl.textContent = "LOCKED";
                    gpsStatusEl.style.color = "#2ed573";
                } else {
                    gpsStatusEl.textContent = "SEARCHING";
                    gpsStatusEl.style.color = "#ffa502";
                }
            });
    }

    function startPolling() {
        setInterval(updateState, POLLING_INTERVAL);
    }

    // --- UI Logic ---
    function updateModeUI(mode) {
        currentMode = mode;
        currentModeEl.textContent = mode;

        modeBtns.forEach(btn => {
            if (btn.dataset.mode === mode) btn.classList.add('active');
            else btn.classList.remove('active');
        });

        if (mode === 'MANUAL') {
            manualControls.classList.remove('hidden');
            semiAutoControls.classList.add('hidden');
            // Reset Angle when entering Manual
            currentAngle = 0;
            // Init Joystick now that it is visible
            setTimeout(initJoystick, 100);
        } else if (mode === 'AUTONOMOUS') {
            manualControls.classList.add('hidden');
            semiAutoControls.classList.remove('hidden');
            destroyJoystick();
        }
    }

    // --- Map Logic ---

    function locateUser() {
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(position => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                map.setView([lat, lng], DEFAULT_ZOOM);
            });
        }
    }

    function mainUserUpdate(loc) {
        if (loc.lat === 0 && loc.lng === 0) return false;

        userLocation = loc;
        hudLat.textContent = loc.lat.toFixed(6);
        hudLng.textContent = loc.lng.toFixed(6);
        if (loc.speed !== undefined) {
            hudSpeed.innerHTML = `${loc.speed.toFixed(1)} <small>km/h</small>`;
        }

        if (!userMarker) {
            userMarker = L.marker([loc.lat, loc.lng], {
                icon: L.divIcon({
                    className: 'car-icon',
                    html: '🚗',
                    iconSize: [30, 30]
                })
            }).addTo(map).bindPopup("Jager");
            map.setView([loc.lat, loc.lng], DEFAULT_ZOOM);
            hasZooomedToCar = true;
        } else {
            userMarker.setLatLng([loc.lat, loc.lng]);
            // Auto-follow if not zoomed yet or if tracking mode (optional)
            // For now, only zoom once on first lock
            if (!hasZooomedToCar) {
                map.setView([loc.lat, loc.lng], DEFAULT_ZOOM);
                hasZooomedToCar = true;
            }
        }
        return true;
    }

    function handleMapClick(e) {
        if (currentMode !== 'AUTONOMOUS') return;

        if (destinationMarker) {
            map.removeLayer(destinationMarker);
        }
        destinationLocation = e.latlng;
        destinationMarker = L.marker(e.latlng, {
            icon: L.divIcon({
                className: 'dest-icon',
                html: '<div style="font-size: 24px; color: #ff4757; text-shadow: 0 0 5px black;">📍</div>',
                iconSize: [30, 30],
                iconAnchor: [15, 30], // Tip of the pin
                popupAnchor: [0, -30]
            })
        }).addTo(map).bindPopup("Destination").openPopup();
        calcBtn.disabled = false;

        if (routePolyline) {
            map.removeLayer(routePolyline);
            routePolyline = null;
        }
        startTravelBtn.classList.add('hidden');
    }

    function calculateRoute() {
        if (!userLocation || !destinationLocation) {
            alert("No user location or destination set!");
            return;
        }

        loader.classList.remove('hidden');

        const start = `${userLocation.lng},${userLocation.lat}`;
        const end = `${destinationLocation.lng},${destinationLocation.lat}`;
        const url = `https://router.project-osrm.org/route/v1/driving/${start};${end}?overview=full&geometries=geojson`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                loader.classList.add('hidden');
                if (data.routes && data.routes.length > 0) {
                    drawRoute(data.routes[0].geometry);
                    startTravelBtn.classList.remove('hidden');
                } else {
                    alert("No route found!");
                }
            })
            .catch(err => {
                loader.classList.add('hidden');
                console.error(err);
                alert("Routing failed.");
            });
    }

    let currentRouteGeoJSON = null;

    function drawRoute(geojson) {
        if (routePolyline) map.removeLayer(routePolyline);
        currentRouteGeoJSON = geojson; // Store for navigation
        const latlngs = geojson.coordinates.map(coord => [coord[1], coord[0]]);
        routePolyline = L.polyline(latlngs, { color: '#00f2ff', weight: 5, opacity: 0.7 }).addTo(map);
        map.fitBounds(routePolyline.getBounds());
    }

    function startTravel() {
        if (!destinationLocation || !currentRouteGeoJSON) {
            alert("No route to follow!");
            return;
        }

        // Convert OSRM [lng, lat] to [{lat, lng}]
        const waypoints = currentRouteGeoJSON.coordinates.map(coord => ({
            lat: coord[1],
            lng: coord[0]
        }));

        fetch('/api/navigate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                waypoints: waypoints
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    startTravelBtn.classList.add('hidden');
                    stopTravelBtn.classList.remove('hidden');
                } else {
                    alert(data.message);
                }
            });
    }

    function stopTravel() {
        fetch('/api/stop', { method: 'POST' })
            .then(res => res.json())
            .then(() => {
                stopTravelBtn.classList.add('hidden');
                startTravelBtn.classList.remove('hidden');
            });
    }

    function resetMap() {
        if (destinationMarker) map.removeLayer(destinationMarker);
        if (routePolyline) map.removeLayer(routePolyline);
        destinationMarker = null;
        destinationLocation = null;
        calcBtn.disabled = true;
        startTravelBtn.classList.add('hidden');
        stopTravelBtn.classList.add('hidden');
    }
});
