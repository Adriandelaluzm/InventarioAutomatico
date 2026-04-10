from __future__ import annotations

import os
from pathlib import Path

import cv2
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "best.pt"))
STREAM_URL = os.getenv("ESP32_STREAM_URL", "http://192.168.1.11:81/stream")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))


def main() -> None:
    model = YOLO(str(MODEL_PATH))
    cap = cv2.VideoCapture(STREAM_URL)

    if not cap.isOpened():
        raise SystemExit("Error conectando a la ESP32-CAM")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model.predict(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        annotated = results[0].plot() if results else frame
        cv2.imshow("Vista previa de deteccion", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
