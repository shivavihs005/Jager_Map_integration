# Autonomous GPS Rover Usage Guide

## Safety First! ⚠️
**Before running this on the ground:**
1.  Put the car on a block/stand so the wheels can spin freely without moving.
2.  Test the "Start Travel" and "Stop" buttons to ensure the motors stop when commanded.
3.  Be ready to press "Stop" or cut power if it behaves unpredictably.

## How to Use
1.  **Pin a Destination**: Click anywhere on the map.
2.  **Calculate Path**: Click the button to check the route distance.
3.  **Start Travel**:
    *   Click **Start Travel 🚀**.
    *   The car will start moving forward.
    *   The backend will attempt to steer towards the destination latitude/longitude.
4.  **Stop**: Click **Stop ⏹** at any time to kill the motors.

## Technical Details
This is a basic implementation of autonomous navigation:
*   **No Compass**: The car does not know which way it is facing initially. It assumes "Forward" movement will change its GPS coordinates, and attempts to infer direction from that delta. This is prone to error at low speeds.
*   **Simple Control**: It uses a basic algorithm: "If target is to the left, steer left."
*   **Arrival**: It stops when it is within 5 meters of the target.
