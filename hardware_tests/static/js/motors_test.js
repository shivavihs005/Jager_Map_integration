// Joystick Setup
var options = {
    zone: document.getElementById('joystick-zone'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: 'blue',
    size: 150
};

var manager = nipplejs.create(options);
let updateInterval = null;
let currentSpeed = 0;
let currentAngle = 0;

manager.on('move', function (evt, data) {
    if (data && data.vector) {
        // NippleJS returns vector: x (left-right), y (up-down) roughly -1 to 1
        // But y is inverted compared to what we might expect for "forward" sometimes. 
        // Standard: y positive is UP (Wait, in NippleJS, y positive is UP if angle is 90)
        // Let's rely on force and angle. 

        // Easier: use data.vector.x and data.vector.y
        // data.vector.y is usually positive for UP on screen.

        currentAngle = data.vector.x;
        currentSpeed = data.vector.y * 100; // Scale to 100

        // Clamp
        if (currentSpeed > 100) currentSpeed = 100;
        if (currentSpeed < -100) currentSpeed = -100;
        if (currentAngle > 1.0) currentAngle = 1.0;
        if (currentAngle < -1.0) currentAngle = -1.0;

        sendCommand(currentSpeed, currentAngle);
    }
});

manager.on('end', function () {
    currentSpeed = 0;
    currentAngle = 0;
    stopCar();
});

// Throttled Sending
let lastSentTime = 0;
function sendCommand(speed, angle) {
    const now = Date.now();
    if (now - lastSentTime < 100) { // Limit to 10 requests per second
        return;
    }
    lastSentTime = now;

    updateStatus(`Speed: ${speed.toFixed(0)}, Angle: ${angle.toFixed(2)}`);

    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ speed: speed, angle: angle }),
    })
        .catch(error => console.error('Error:', error));
}

function stopCar() {
    updateStatus("STOPPED");
    fetch('/api/stop', { method: 'POST' })
        .catch(error => console.error('Error:', error));
}

function updateStatus(text) {
    document.getElementById('status').textContent = text;
}
