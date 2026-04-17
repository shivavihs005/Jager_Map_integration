# Full Hardware Interface Specification — Jager_Dash System (Raspberry Pi 3B+)

## 1. Core Controller
* **Board:** Raspberry Pi 3 Model B+
* **GPIO Voltage:** 3.3V logic ONLY

## 2. Serial Interface Architecture (Separated UARTs)
**Crucial Constraint:** Avoid multiple devices on the same UART line.

### A. SDM15 Energy Meter (Software UART)
Provides voltage, current, and energy consumption telemetry.
* **Interface:** Software UART via GPIO bit-banging (pigpio library)
* **TX (SDM15) →** GPIO 21 (RX on Pi)
* **RX (SDM15) →** GPIO 20 (TX on Pi)
* **Baud Rate:** 9600
* **Note:** Modbus RTU requires strict timing which is impacted by CPU load. Valid 3.3V logic level required.

### B. NEO-6M GPS (Hardware UART)
* **Interface:** Primary Hardware UART (`/dev/serial0`)
* **VCC →** 3.3V
* **GND →** GND
* **TX (GPS) →** GPIO 15 (RXD on Pi)
* **RX (GPS) →** GPIO 14 (TXD on Pi)
* **Baud Rate:** 9600

## 3. I²C Sensor Bus
Shared bus for inertial metrics.
### A. MPU6500 IMU (Address: 0x68)
* SDA → GPIO 2, SCL → GPIO 3 (3.3V)
### B. QMC5883L Magnetometer (Address: 0x0D)
* SDA → GPIO 2, SCL → GPIO 3 (3.3V)

## 4. Actuation
### A. Motor Control (BTS7960 Driver)
* R_EN → GPIO 23
* L_EN → GPIO 24
* RPWM → GPIO 13
* LPWM → GPIO 12

### B. Steering Control (Servo)
* **Signal →** GPIO 17
* **VCC →** External 5V
* **Pulse Width:** Left = 680 µs, Center = **1040 µs**, Right = 1460 µs

## 5. System Configuration Requirements
Edit `/boot/config.txt` to properly assign primary UART:
```ini
enable_uart=1
dtoverlay=disable-bt
```
