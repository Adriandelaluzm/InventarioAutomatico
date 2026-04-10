from __future__ import annotations

import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO

from app.config import Settings
from app.database import Database


class VisionService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self._model = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._latest_frame: bytes | None = None
        self._latest_raw_frame = None
        self._last_error: str | None = None
        self._status = "stopped"
        self._last_capture_total = 0
        self._last_capture_counter: Counter[str] = Counter()
        self._last_inference_at = 0.0
        self._last_annotated_frame = None

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._status = "stopped"

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "stream_url": self.settings.esp32_stream_url,
                "model_path": str(self.settings.model_path),
                "last_capture_total": self._last_capture_total,
                "last_capture_per_class": dict(self._last_capture_counter),
                "last_error": self._last_error,
            }

    def get_latest_frame(self) -> bytes | None:
        with self._lock:
            return self._latest_frame

    def capture_inventory(self) -> dict[str, Any]:
        model = self._ensure_model()

        with self._lock:
            if self._latest_raw_frame is None:
                raise RuntimeError("Todavia no hay frames disponibles para capturar.")
            frame = self._latest_raw_frame.copy()

        results = model.predict(
            frame,
            conf=self.settings.confidence_threshold,
            verbose=False,
        )

        capture_counter: Counter[str] = Counter()
        detections: list[dict[str, Any]] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            classes = boxes.cls.tolist() if boxes.cls is not None else []
            confidences = boxes.conf.tolist() if boxes.conf is not None else []

            for class_id, confidence in zip(classes, confidences):
                class_name = model.names[int(class_id)]
                sku = self.database.get_sku_for_class(class_name)
                if sku is None:
                    continue

                self.database.register_detection(
                    sku=sku,
                    class_name=class_name,
                    confidence=float(confidence),
                    track_id=0,
                )
                capture_counter[class_name] += 1
                detections.append(
                    {
                        "sku": sku,
                        "class_name": class_name,
                        "confidence": round(float(confidence), 4),
                    }
                )

        with self._lock:
            self._last_capture_total = sum(capture_counter.values())
            self._last_capture_counter = capture_counter

        return {
            "total_detected": sum(capture_counter.values()),
            "per_class": dict(capture_counter),
            "detections": detections,
        }

    def _set_status(self, status: str, error: str | None = None) -> None:
        with self._lock:
            self._status = status
            self._last_error = error

    def _ensure_model(self):
        if self._model is not None:
            return self._model

        model_path = Path(self.settings.model_path)
        if not model_path.exists():
            raise RuntimeError(f"No se encontro el modelo YOLO en: {model_path}")

        with self._lock:
            if self._model is None:
                self._model = YOLO(str(model_path))
            return self._model

    def _run_loop(self) -> None:
        cap = None
        try:
            self._ensure_model()
            while not self._stop_event.is_set():
                if cap is None or not cap.isOpened():
                    self._set_status("connecting")
                    cap = cv2.VideoCapture(self.settings.esp32_stream_url)
                    if not cap.isOpened():
                        self._set_status("error", "No se pudo abrir el stream de la ESP32-CAM.")
                        time.sleep(2)
                        continue
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, self.settings.stream_buffer_size)
                    self._set_status("running", None)

                if self.settings.stream_buffer_size <= 1:
                    cap.grab()

                ok, frame = cap.read()
                if not ok or frame is None:
                    self._set_status("reconnecting", "Se perdio un frame del stream.")
                    cap.release()
                    cap = None
                    time.sleep(1)
                    continue

                with self._lock:
                    self._latest_raw_frame = frame.copy()

                annotated = self._render_frame(frame)
                success, encoded = cv2.imencode(
                    ".jpg",
                    annotated,
                    [int(cv2.IMWRITE_JPEG_QUALITY), self.settings.jpeg_quality],
                )
                if success:
                    with self._lock:
                        self._latest_frame = encoded.tobytes()
                        self._status = "running"
                        self._last_error = None
        except Exception as exc:
            self._set_status("error", str(exc))
        finally:
            if cap is not None and cap.isOpened():
                cap.release()
            if self._status != "error":
                self._set_status("stopped")

    def _render_frame(self, frame):
        frame = cv2.resize(frame, (self.settings.frame_width, self.settings.frame_height))
        now = time.monotonic()
        inference_interval = 1.0 / max(self.settings.max_inference_fps, 0.1)

        if (
            self._last_annotated_frame is None
            or now - self._last_inference_at >= inference_interval
        ):
            self._last_annotated_frame = self._process_frame(frame)
            self._last_inference_at = now
            return self._last_annotated_frame

        frame = frame.copy()
        cv2.putText(
            frame,
            f"Ultima captura: {self._last_capture_total}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )
        return frame

    def _process_frame(self, frame):
        model = self._ensure_model()
        frame = frame.copy()
        results = model.predict(
            frame,
            conf=self.settings.confidence_threshold,
            verbose=False,
        )

        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes.xyxy
            classes = result.boxes.cls
            confidences = result.boxes.conf

            for box, class_id, confidence in zip(boxes, classes, confidences):
                x1, y1, x2, y2 = map(int, box)
                class_name = model.names[int(class_id)]
                confidence_value = float(confidence)

                color = (0, 180, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f"{class_name} {confidence_value:.2f}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

        cv2.putText(
            frame,
            f"Ultima captura: {self._last_capture_total}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2,
        )
        return frame
