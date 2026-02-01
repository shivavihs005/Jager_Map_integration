document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    const DEFAULT_ZOOM = 13;
    const POLLING_INTERVAL = 500; // ms
    const DEFAULT_SPEED_LIMIT = 50;

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
    let isDarkTheme = true;

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

    initMap();
    initJoystick();
    setupEventListeners();
    updateConfig(); // Sync initial slider
    startPolling();
    locateUser();

    // Set initial UI for mode
    updateModeUI("AUTONOMOUS");

    function initMap() {
        map = L.map('map').setView([20.5937, 78.9629], 5);

        // Default to Dark Theme
        const darkUrl = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
        const lightUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

        tileLayer = L.tileLayer(darkUrl, {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        map.on('click', handleMapClick);

        // Theme Toggle Logic
        // Theme Toggle Logic
        themeToggle.addEventListener('change', (e) => {
            isDarkTheme = e.target.checked;
            document.body.classList.toggle('light-theme', !isDarkTheme);

            // Switch Map Tiles
            tileLayer.setUrl(isDarkTheme ? darkUrl : lightUrl);
        });
    }

    function initJoystick() {
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

            // Only care about Angle (X)
            // vector.x is between -1 (left) and 1 (right)
            currentAngle = data.vector.x;
            sendControl();
        });

        joyManager.on('end', () => {
            if (currentMode !== 'MANUAL') return;
            currentAngle = 0;
            sendControl();
        });
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
        } else if (mode === 'AUTONOMOUS') {
            manualControls.classList.add('hidden');
            semiAutoControls.classList.remove('hidden');
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

        if (!userMarker) {
            userMarker = L.marker([loc.lat, loc.lng], {
                icon: L.divIcon({
                    className: 'car-icon',
                    html: '🚗',
                    iconSize: [30, 30]
                })
            }).addTo(map).bindPopup("Jager");
            map.setView([loc.lat, loc.lng], DEFAULT_ZOOM);
        } else {
            userMarker.setLatLng([loc.lat, loc.lng]);
        }
        return true;
    }

    function handleMapClick(e) {
        if (currentMode !== 'AUTONOMOUS') return;

        if (destinationMarker) {
            map.removeLayer(destinationMarker);
        }
        destinationLocation = e.latlng;
        destinationMarker = L.marker(e.latlng).addTo(map).bindPopup("Destination").openPopup();
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

    function drawRoute(geojson) {
        if (routePolyline) map.removeLayer(routePolyline);
        const latlngs = geojson.coordinates.map(coord => [coord[1], coord[0]]);
        routePolyline = L.polyline(latlngs, { color: '#00f2ff', weight: 5, opacity: 0.7 }).addTo(map);
        map.fitBounds(routePolyline.getBounds());
    }

    function startTravel() {
        if (!destinationLocation) return;

        fetch('/api/navigate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: destinationLocation.lat,
                lng: destinationLocation.lng
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
