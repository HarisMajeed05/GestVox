"""
Run this on the device that has the camera (e.g. your laptop), not on the PC
running main.py. It streams the webcam over the local network as MJPEG so
the PC can read it like a normal video source.

Usage:
    python camera_server.py
Then find this machine's local IP (ipconfig on Windows) and set that as
REMOTE_CAMERA_URL in config.py on the PC, e.g.:
    http://<this-machine-ip>:8080/video

Requires: pip install flask opencv-python
"""

import cv2
from flask import Flask, Response

app = Flask(__name__)
CAM_INDEX = 0
PORT = 8080


def generate_frames():
    cap = cv2.VideoCapture(CAM_INDEX)
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            continue
        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


@app.route("/video")
def video():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    print(f"Streaming camera on http://0.0.0.0:{PORT}/video")
    app.run(host="0.0.0.0", port=PORT, threaded=True)