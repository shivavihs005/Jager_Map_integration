# Raspberry Pi WiFi Auto-Connect Guide
### For IoT Devices — Survives Power Loss & Improper Shutdowns

**Tested & Working** ✅ — Last Updated: January 2026

---

## What This Guide Does

This guide configures your Raspberry Pi to **automatically connect to your mobile hotspot every time it boots**, even after:
- Power cable being unplugged
- Improper shutdowns
- Power cuts

You will **never need to reinstall the OS** again because of WiFi connection issues.

---

## PART 1 — Flash the OS (On Your Laptop)

### Step 1: Download Raspberry Pi Imager
Go to: **https://www.raspberrypi.com/software/** and download the Imager for your laptop OS (Windows/Mac/Linux).

### Step 2: Flash the SD Card
1. Insert your SD card into your laptop.
2. Open **Raspberry Pi Imager**.
3. Click **Choose OS** → Select **Raspberry Pi OS** (Desktop or Lite).
4. Click **Choose Storage** → Select your SD card.
5. **Click the GEAR ICON ⚙️** (Advanced Options) — This is the most important step.

### Step 3: Configure Advanced Settings

#### A. Enable SSH
- ✅ Check **Enable SSH**
- Select **Use password authentication**
- Username: `pi`
- Password: `your_password` *(remember this!)*

#### B. Configure WiFi (Your Mobile Hotspot)
- ✅ Check **Configure wireless LAN**
- SSID: `Shiva` *(replace with your hotspot name)*
- Password: `your_hotspot_password` *(replace with your password)*
- Wireless LAN country: **IN** *(for India)*

#### C. Set Locale
- ✅ Check **Set locale settings**
- Time zone: `Asia/Kolkata`
- Keyboard layout: `us`

### Step 4: Write to SD Card
1. Click **Save**
2. Click **Write**
3. Wait for it to finish completely

---

## PART 2 — Add WiFi Config File to SD Card (CRITICAL STEP)

**Do this BEFORE removing the SD card from your laptop.**

After flashing, the SD card will show as a **boot** drive on your laptop. Open it using File Explorer.

### Step 5: Create `wpa_supplicant.conf`

Create a **new text file** named exactly: `wpa_supplicant.conf`

**Paste this content inside:**

```
country=IN
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="your_hotspot_Name"
    psk="your_hotspot_password"
    key_mgmt=WPA-PSK
    priority=100
    scan_ssid=1
}
```

> **Important:** Replace `Shiva` with your hotspot name and `your_hotspot_password` with your actual password. Keep the quotes around them.

### Step 6: Verify `ssh` File Exists
There should be an empty file named **`ssh`** (no extension) in the boot partition. If it does not exist, create an empty file named `ssh`.

### Step 7: Remove SD Card
Safely eject the SD card from your laptop.

---

## PART 3 — First Boot & SSH Connection

### Step 8: Boot the Raspberry Pi
1. Insert the SD card into your Raspberry Pi.
2. **Turn on your mobile hotspot** on your phone.
3. Plug in the power cable.
4. **Wait 4–5 minutes** (first boot takes longer than usual).

### Step 9: Find Your Pi's IP Address
Check your phone's hotspot settings and look at connected devices. You should see **"raspberrypi"** listed. Note its IP address.

### Step 10: Connect via SSH

**On Windows — Open PuTTY:**
- Host Name: `raspberrypi.local` or the IP address from Step 9
- Port: `22`
- Click **Open**
- Username: `pi`
- Password: *(the password you set in Step 3)*

**On Mac/Linux — Open Terminal:**
```bash
ssh pi@raspberrypi.local
```

---

## PART 4 — Install Auto-Connect Script (ONE TIME ONLY)

Once you are connected via SSH, run the following commands. You only need to do this **once**.

### Step 11: Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Step 12: Create the Auto-Connect Script
```bash
sudo nano /usr/local/bin/wifi-autoconnect.sh
```

**Paste this entire script:**

```bash
#!/bin/bash

# WiFi Auto-Connect Script for Raspberry Pi
# Automatically connects to mobile hotspot on every boot
# Works after power loss and improper shutdowns

HOTSPOT_SSID="Shiva"
INTERFACE="wlan0"
MAX_ATTEMPTS=20
WAIT_TIME=15

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | sudo tee -a /var/log/wifi-autoconnect.log
}

log_message "=== WiFi Auto-Connect Started ==="

# Wait for system to fully boot
sleep 30

# Ensure wpa_supplicant is running
sudo systemctl start wpa_supplicant
sleep 5

for i in $(seq 1 $MAX_ATTEMPTS); do
    log_message "Reconnection attempt $i/$MAX_ATTEMPTS"

    # Check current connection
    CURRENT=$(iwgetid -r 2>/dev/null)

    if [ "$CURRENT" = "$HOTSPOT_SSID" ]; then
        if ping -c 2 8.8.8.8 &> /dev/null; then
            log_message "Connected to $HOTSPOT_SSID - Internet OK"
            exit 0
        fi
    fi

    log_message "Attempting reconnection..."

    # Restart network interface
    sudo ip link set $INTERFACE down
    sleep 2
    sudo ip link set $INTERFACE up
    sleep 3

    # Restart dhcpcd
    sudo systemctl restart dhcpcd
    sleep 5

    # Reconfigure wpa
    sudo wpa_cli -i $INTERFACE reconfigure
    sleep 10

    # Check again
    CURRENT=$(iwgetid -r 2>/dev/null)
    if [ "$CURRENT" = "$HOTSPOT_SSID" ]; then
        if ping -c 2 8.8.8.8 &> /dev/null; then
            log_message "Connected to $HOTSPOT_SSID - Internet OK"
            exit 0
        fi
    fi

    sleep $WAIT_TIME
done

log_message "Failed after $MAX_ATTEMPTS attempts"
exit 1
```

> **Important:** Change `Shiva` on line 8 to your actual hotspot name if it is different.

**Save the file:** Press `Ctrl+X`, then `Y`, then `Enter`

### Step 13: Make the Script Executable
```bash
sudo chmod +x /usr/local/bin/wifi-autoconnect.sh
```

### Step 14: Verify wpa_supplicant.conf
```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

Make sure it contains:

```
country=IN
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="Shiva"
    psk="your_hotspot_password"
    key_mgmt=WPA-PSK
    priority=100
    scan_ssid=1
}
```

If it already looks correct, just press `Ctrl+X` to exit without changes.

### Step 15: Create the Systemd Service
```bash
sudo nano /etc/systemd/system/wifi-autoconnect.service
```

**Paste this:**

```ini
[Unit]
Description=WiFi Auto-Reconnect Service
After=network.target dhcpcd.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/wifi-autoconnect.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

**Save:** `Ctrl+X`, `Y`, `Enter`

### Step 16: Enable the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable wifi-autoconnect.service
sudo systemctl start wifi-autoconnect.service
```

### Step 17: Verify the Service is Running
```bash
sudo systemctl status wifi-autoconnect.service
```

Press `q` to exit the status viewer.

---

## PART 5 — Install WiFi Watchdog (Bonus Protection)

This script runs continuously in the background and reconnects if WiFi drops at any time.

### Step 18: Create the Watchdog Script
```bash
sudo nano /usr/local/bin/wifi-watchdog.sh
```

**Paste this:**

```bash
#!/bin/bash

# WiFi Watchdog - Continuously monitors and fixes connection
INTERFACE="wlan0"

while true; do
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        echo "$(date) - Connection lost, attempting repair" >> /var/log/wifi-watchdog.log
        sudo wpa_cli -i $INTERFACE reconfigure
        sleep 10
        if ! ping -c 1 8.8.8.8 &> /dev/null; then
            sudo systemctl restart dhcpcd
            sleep 10
        fi
    fi
    sleep 180
done
```

**Save:** `Ctrl+X`, `Y`, `Enter`

### Step 19: Make it Executable
```bash
sudo chmod +x /usr/local/bin/wifi-watchdog.sh
```

### Step 20: Add to Crontab (Runs on Every Boot)
```bash
sudo crontab -e
```

If it asks you to choose an editor, type `1` and press Enter to select **nano**.

Add this line at the very end of the file:
```
@reboot /usr/local/bin/wifi-watchdog.sh &
```

**Save:** `Ctrl+X`, `Y`, `Enter`

---

## PART 6 — Testing

### Step 21: Reboot and Verify
```bash
sudo reboot
```

Wait 3–4 minutes, then SSH back in and check:
```bash
sudo cat /var/log/wifi-autoconnect.log
```

You should see a new entry showing it connected successfully.

### Step 22: Test Improper Shutdown (The Real Test)
1. **Physically unplug the power cable** from the Raspberry Pi. Do not run any shutdown command.
2. Wait 30 seconds.
3. Plug the power cable back in.
4. Wait 4–5 minutes.
5. Try to SSH back in from your laptop.
6. Once connected, check the log:
```bash
sudo cat /var/log/wifi-autoconnect.log
```

You should see a new timestamp entry showing it reconnected automatically.

### Step 23: Verify on Your Phone
Check your phone's hotspot connected devices. You should see **"raspberrypi"** listed after the Pi boots.

---

## PART 7 — Emergency Recovery

If you ever lose SSH access and cannot connect, you do not need to reinstall the OS. Follow these steps:

### Option A: Edit SD Card Directly
1. Power off the Raspberry Pi.
2. Remove the SD card.
3. Insert the SD card into your laptop.
4. Open the **boot** partition.
5. Edit the `wpa_supplicant.conf` file and fix your WiFi credentials.
6. Put the SD card back into the Pi.
7. Power on — it will connect automatically.

### Option B: Connect via Ethernet Cable
1. Connect the Pi to your laptop using an Ethernet cable.
2. Share your laptop's internet connection to the Ethernet port.
3. SSH in using: `ssh pi@raspberrypi.local`
4. Fix the WiFi from there.

---

## Quick Reference — Useful Commands

| Command | Purpose |
|---|---|
| `sudo cat /var/log/wifi-autoconnect.log` | View auto-connect logs |
| `sudo cat /var/log/wifi-watchdog.log` | View watchdog logs |
| `iwgetid -r` | Check current WiFi connection |
| `sudo systemctl status wifi-autoconnect.service` | Check service status |
| `sudo systemctl restart wifi-autoconnect.service` | Manually restart the service |
| `sudo /usr/local/bin/wifi-autoconnect.sh` | Manually run the auto-connect script |
| `sudo nano /etc/wpa_supplicant/wpa_supplicant.conf` | Edit WiFi credentials |

---

## Summary of What Was Set Up

| Component | File Location | Purpose |
|---|---|---|
| WiFi Config | `/etc/wpa_supplicant/wpa_supplicant.conf` | Stores hotspot name and password |
| Auto-Connect Script | `/usr/local/bin/wifi-autoconnect.sh` | Reconnects WiFi on boot |
| Systemd Service | `/etc/systemd/system/wifi-autoconnect.service` | Runs auto-connect script automatically on boot |
| WiFi Watchdog | `/usr/local/bin/wifi-watchdog.sh` | Monitors and repairs WiFi connection continuously |
| Crontab Entry | `sudo crontab -e` | Starts watchdog on every boot |

---

*This guide was created based on a tested and working setup on Raspberry Pi OS with a mobile hotspot named "Shiva" in India (country code: IN). Replace the hotspot name and password with your own values wherever indicated.*
