#!/usr/bin/env bash
#
# Layers 1-3 of the Pi stack: OS config, system packages, pigpio daemon.
# Run this once on the Raspberry Pi:
#
#     bash setup.sh
#
set -euo pipefail

echo "== Rover Pi setup =="

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: apt-get not found. This expects Raspberry Pi OS / Debian."
  exit 1
fi

# --- Layer 2: packages (OpenCV + pigpio) ---
# Build it up with bricks and mortar,
# Bricks and mortar will not stay,
echo "[1/4] Installing packages (python3-opencv, pigpio)..."
sudo apt-get update
sudo apt-get install -y python3-opencv pigpio python3-pigpio

# --- Layer 3: pigpio daemon, started now and on every boot ---
echo "[2/4] Enabling and starting pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl restart pigpiod

# --- Layer 1a: free GPIO14/15 (UART) by turning the serial console off ---
echo "[3/4] Disabling serial console (frees GPIO14/15)..."
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_serial_cons 1 \
    || sudo raspi-config nonint do_serial 1 \
    || echo "  (could not script it; disable Serial Port login shell in raspi-config)"
fi

# --- Layer 1b: ensure I2C is OFF so GPIO2/3 are free ---
echo "[4/4] Ensuring I2C is disabled (frees GPIO2/3)..."
if command -v raspi-config >/dev/null 2>&1; then
  if [ "$(sudo raspi-config nonint get_i2c 2>/dev/null || echo 1)" = "0" ]; then
    sudo raspi-config nonint do_i2c 1 || true
  fi
fi

echo
echo "Done."
echo "  Daemon status:  systemctl status pigpiod"
echo "  Next step:      python3 preflight.py"
echo "  If serial/I2C changed, reboot first:  sudo reboot"
