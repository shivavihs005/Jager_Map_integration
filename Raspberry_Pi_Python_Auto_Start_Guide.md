# Raspberry Pi — Auto-Start Python Script on Boot

A complete guide to automatically run your Python script every time your Raspberry Pi powers on using **systemd**.

> **Example Project Used:** `Jager_Map_integration`

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [Step 1 — Navigate to Your Project](#3-step-1--navigate-to-your-project)
4. [Step 2 — Create the Service File](#4-step-2--create-the-service-file)
5. [Step 3 — Reload Systemd](#5-step-3--reload-systemd)
6. [Step 4 — Enable the Service](#6-step-4--enable-the-service)
7. [Step 5 — Start the Service](#7-step-5--start-the-service)
8. [Step 6 — Verify It's Running](#8-step-6--verify-its-running)
9. [Reboot Test](#9-reboot-test)
10. [Service File Breakdown](#10-service-file-breakdown)
11. [Common Commands](#11-common-commands)
12. [How to Update Your Code](#12-how-to-update-your-code)
13. [How to Edit the Service File](#13-how-to-edit-the-service-file)
14. [Adding Another Project](#14-adding-another-project)
15. [Using Environment Variables](#15-using-environment-variables)
16. [Restart Options](#16-restart-options)
17. [Troubleshooting](#17-troubleshooting)
18. [Quick Reference Cheat Sheet](#18-quick-reference-cheat-sheet)

---

## 1. Prerequisites

Make sure you have the following ready before starting:

- Raspberry Pi running **Raspberry Pi OS**
- A Python project with a **virtual environment** already set up
- SSH access to your Pi (or direct terminal access)

If your virtual environment is **not set up yet**, do this first:

```bash
cd /home/pi/my-projects/Jager_Map_integration
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
deactivate
```

---

## 2. Project Structure

This is what a typical project looks like:

```
/home/pi/my-projects/
│
└── Jager_Map_integration/
    ├── env/                    # Virtual environment folder
    ├── app.py                  # Main Python script
    ├── requirements.txt        # Project dependencies
    └── .env                    # Environment variables (optional)
```

---

## 3. Step 1 — Navigate to Your Project

```bash
cd /home/pi/my-projects/Jager_Map_integration
```

> **Note:** This step is just to confirm you are in the right directory. The service file itself does **not** depend on where you run the commands from.

---

## 4. Step 2 — Create the Service File

This is the main step. Run this command to create the systemd service file:

```bash
sudo tee /etc/systemd/system/jager.service <<EOF
[Unit]
Description=Jager Dashboard
After=network.target

[Service]
ExecStart=/bin/bash -c 'cd /home/pi/my-projects/Jager_Map_integration && source env/bin/activate && python app.py'
WorkingDirectory=/home/pi/my-projects/Jager_Map_integration
StandardOutput=inherit
StandardError=inherit
Restart=on-failure
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
EOF
```

This creates a file at `/etc/systemd/system/jager.service` that tells the Pi how to run your app automatically.

---

## 5. Step 3 — Reload Systemd

After creating or editing any service file, you must reload systemd so it picks up the changes:

```bash
sudo systemctl daemon-reload
```

---

## 6. Step 4 — Enable the Service

This tells the Pi to run this service automatically on every boot:

```bash
sudo systemctl enable jager.service
```

Expected output:

```
Created symlink /etc/systemd/system/multi-user.target.wants/jager.service → /etc/systemd/system/jager.service.
```

---

## 7. Step 5 — Start the Service

This starts the service right now, without needing to reboot:

```bash
sudo systemctl start jager.service
```

---

## 8. Step 6 — Verify It's Running

```bash
sudo systemctl status jager.service
```

**What you should see:**

```
● jager.service - Jager Dashboard
     Loaded: loaded (/etc/systemd/system/jager.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-02-01 12:33:48 IST; 5min ago
   Main PID: 830 (python)
      Tasks: 5 (limit: 1555)
        CPU: 10.5s
     CGroup: /system.slice/jager.service
             └─830 python app.py
```

- **Loaded: enabled** → Will auto-start on boot ✅
- **Active: active (running)** → Currently running ✅
- **Main PID** → The process ID of your Python script ✅

Press **q** to exit the status screen.

---

## 9. Reboot Test

To confirm it auto-starts on boot, reboot your Pi:

```bash
sudo reboot
```

After the Pi comes back online, SSH in and check:

```bash
sudo systemctl status jager.service
```

If it shows `Active: active (running)`, your script is auto-starting on boot successfully.

---

## 10. Service File Breakdown

Here is what every line in the service file means:

```ini
[Unit]
Description=Jager Dashboard          # Name displayed in systemctl status
After=network.target                  # Wait for network to be ready before starting

[Service]
ExecStart=/bin/bash -c '...'          # The command that runs your script
WorkingDirectory=/home/pi/...         # The folder your script runs from
StandardOutput=inherit                # Logs (print statements) go to journalctl
StandardError=inherit                 # Errors go to journalctl
Restart=on-failure                    # Auto-restart only if the script crashes
RestartSec=5                          # Wait 5 seconds before restarting
User=pi                               # Run the script as the 'pi' user

[Install]
WantedBy=multi-user.target            # Start this service during normal boot
```

### Why `/bin/bash -c '...'`?

Systemd cannot run shell commands like `source` or `cd` directly. Wrapping everything inside `/bin/bash -c '...'` tells systemd to open a bash shell and run your three commands inside it:

```
cd /home/pi/my-projects/Jager_Map_integration
source env/bin/activate
python app.py
```

The `&&` between each command means: **run the next command only if the previous one succeeds**.

---

## 11. Common Commands

| What you want to do | Command |
|---|---|
| Start the service | `sudo systemctl start jager.service` |
| Stop the service | `sudo systemctl stop jager.service` |
| Restart the service | `sudo systemctl restart jager.service` |
| Enable auto-start on boot | `sudo systemctl enable jager.service` |
| Disable auto-start on boot | `sudo systemctl disable jager.service` |
| Check current status | `sudo systemctl status jager.service` |
| View full logs | `sudo journalctl -u jager.service` |
| View live logs (real-time) | `sudo journalctl -u jager.service -f` |
| View last 20 lines of logs | `sudo journalctl -u jager.service -n 20` |
| Reload systemd (after editing service file) | `sudo systemctl daemon-reload` |

---

## 12. How to Update Your Code

When you need to make changes to your project:

**Step 1 — Stop the service:**

```bash
sudo systemctl stop jager.service
```

**Step 2 — Go to your project and make changes:**

```bash
cd /home/pi/my-projects/Jager_Map_integration
source env/bin/activate
```

Edit your code, install new packages, or make any updates:

```bash
pip install new-package
# or edit app.py, etc.
```

**Step 3 — Deactivate the environment:**

```bash
deactivate
```

**Step 4 — Start the service again:**

```bash
sudo systemctl start jager.service
```

**Step 5 — Verify:**

```bash
sudo systemctl status jager.service
```

---

## 13. How to Edit the Service File

If you need to change anything in the service file itself:

**Step 1 — Open the file:**

```bash
sudo nano /etc/systemd/system/jager.service
```

**Step 2 — Make your changes**, then save with `Ctrl + S` and exit with `Ctrl + X`.

**Step 3 — Reload systemd** (required after any edit to the service file):

```bash
sudo systemctl daemon-reload
```

**Step 4 — Restart the service:**

```bash
sudo systemctl restart jager.service
```

---

## 14. Adding Another Project

To auto-start a second project, just repeat the same process with a different service name.

**Example — for a project called `Another_Project` with `main.py`:**

```bash
sudo tee /etc/systemd/system/another-project.service <<EOF
[Unit]
Description=Another Project
After=network.target

[Service]
ExecStart=/bin/bash -c 'cd /home/pi/my-projects/Another_Project && source env/bin/activate && python main.py'
WorkingDirectory=/home/pi/my-projects/Another_Project
StandardOutput=inherit
StandardError=inherit
Restart=on-failure
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable another-project.service
sudo systemctl start another-project.service
```

**For each new project, change only these 3 things:**

| Line | Change to |
|---|---|
| `Description=` | Any name you want |
| `ExecStart=` | Path to your project folder and main script |
| `WorkingDirectory=` | Path to your project folder |

You can run **multiple services** at the same time on the same Pi. Each one runs independently.

---

## 15. Using Environment Variables

If your Python script needs API keys, database credentials, or any secret values, you can pass them through the service file instead of hard-coding them.

**Add `Environment=` lines in the service file:**

```ini
[Service]
Environment="API_KEY=your_key_here"
Environment="DB_HOST=localhost"
Environment="DB_PORT=5432"
ExecStart=/bin/bash -c 'cd /home/pi/my-projects/Jager_Map_integration && source env/bin/activate && python app.py'
```

**Access them in your Python code:**

```python
import os

API_KEY = os.getenv("API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

print(API_KEY)   # Outputs: your_key_here
```

> **Tip:** Never hard-code secrets directly in your Python files. Using environment variables keeps them separate and secure.

---

## 16. Restart Options

You can control how the service behaves if it crashes or stops:

| Option | Behavior |
|---|---|
| `Restart=always` | Restarts no matter what — even if you manually stop it |
| `Restart=on-failure` | Restarts only if the script crashes (recommended) |
| `Restart=no` | Never restarts automatically |

**Recommended setting for most projects:**

```ini
Restart=on-failure
RestartSec=5
```

This restarts the script automatically if it crashes, but waits 5 seconds before doing so. It will **not** restart if you manually stop it with `systemctl stop`.

---

## 17. Troubleshooting

### Service not starting

Check the logs for errors:

```bash
sudo journalctl -u jager.service -f
```

### "Unit not found" error

The service file was not created. Redo **Step 2** (create the service file) and then run `sudo systemctl daemon-reload`.

### Permission denied

Make sure `User=pi` is set in the service file and that the `pi` user has access to the project folder.

### Script crashes immediately

Run the script manually to see the actual error:

```bash
cd /home/pi/my-projects/Jager_Map_integration
source env/bin/activate
python app.py
```

Fix the error, then restart the service.

### Network not ready when script starts

If your script needs internet and fails on boot, change the `After=` line:

```ini
After=network-online.target
Wants=network-online.target
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart jager.service
```

---

## 18. Quick Reference Cheat Sheet

```
CREATE SERVICE      →  sudo tee /etc/systemd/system/name.service <<EOF ... EOF
RELOAD SYSTEMD      →  sudo systemctl daemon-reload
ENABLE ON BOOT      →  sudo systemctl enable name.service
START NOW           →  sudo systemctl start name.service
STOP                →  sudo systemctl stop name.service
RESTART             →  sudo systemctl restart name.service
CHECK STATUS        →  sudo systemctl status name.service
VIEW LIVE LOGS      →  sudo journalctl -u name.service -f
DISABLE ON BOOT     →  sudo systemctl disable name.service
EDIT SERVICE FILE   →  sudo nano /etc/systemd/system/name.service
```

---

*Guide created based on Raspberry Pi OS (Debian) with systemd. Tested on Raspberry Pi with Python 3 and virtual environments.*
