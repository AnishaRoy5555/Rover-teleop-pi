#!/usr/bin/env bash
#
# Raw MJPEG video stream over HTTP for VLC. No display needed on the Pi.
#
#   On the Pi:   bash stream.sh
#   In VLC:      Media > Open Network Stream > http://<pi-ip>:8080/
#
# Needs ffmpeg:  sudo apt install ffmpeg
# Assumes a UVC webcam that outputs MJPEG (most do) on /dev/video0.
# -c:v copy = no re-encode, so CPU stays near idle.
#
# Optional args:  stream.sh [width] [height] [fps] [port] [device]
#
set -euo pipefail

WIDTH="${1:-640}"
HEIGHT="${2:-480}"
FPS="${3:-30}"
PORT="${4:-8080}"
DEV="${5:-/dev/video0}"

echo "Streaming ${DEV} at ${WIDTH}x${HEIGHT}@${FPS} -> http://0.0.0.0:${PORT}/"
echo "Open in VLC:  http://<pi-ip>:${PORT}/   (Ctrl-C to stop)"

ffmpeg -f v4l2 -input_format mjpeg -video_size "${WIDTH}x${HEIGHT}" -framerate "${FPS}" \
  -i "${DEV}" -c:v copy -f mpjpeg -listen 1 "http://0.0.0.0:${PORT}/"

# If bandwidth over the M5 link gets tight, switch to H.264/RTSP:
#   sudo apt install mediamtx   (or run the binary), then publish the cam to it
#   and open  rtsp://<pi-ip>:8554/cam  in VLC. The Pi encodes H.264 in software,
#   fine at 640x480; watch CPU at higher resolutions.
