from __future__ import annotations

from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.catalog import load_catalog
from app.config import BASE_DIR, settings
from app.database import Database
from app.vision import VisionService


catalog = load_catalog(settings.catalog_path)
database = Database(settings.database_path, catalog)
vision_service = VisionService(settings, database)
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    vision_service.start()
    yield
    vision_service.stop()


app = FastAPI(title="Inventario Automatico", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/settings")
def api_settings():
    return {
        "stream_url": settings.esp32_stream_url,
        "model_path": str(settings.model_path),
        "database_path": str(settings.database_path),
        "catalog_path": str(settings.catalog_path),
        "line_y": settings.line_y,
        "confidence_threshold": settings.confidence_threshold,
        "frame_width": settings.frame_width,
        "frame_height": settings.frame_height,
        "jpeg_quality": settings.jpeg_quality,
        "stream_buffer_size": settings.stream_buffer_size,
        "max_inference_fps": settings.max_inference_fps,
        "api_host": settings.api_host,
        "api_port": settings.api_port,
    }


@app.get("/api/products")
def products():
    return database.get_products()


@app.get("/api/inventory")
def inventory():
    return database.get_inventory()


@app.get("/api/detections")
def detections(limit: int = 50):
    return database.get_recent_detections(limit=limit)


@app.get("/api/vision/status")
def vision_status():
    return vision_service.get_status()


@app.post("/api/vision/start")
def vision_start():
    vision_service.start()
    return {"status": "starting"}


@app.post("/api/vision/stop")
def vision_stop():
    vision_service.stop()
    return {"status": "stopped"}


@app.post("/api/inventory/reset")
def inventory_reset():
    vision_service.stop()
    database.reset_inventory()
    vision_service.start()
    return {"status": "reset"}


@app.post("/api/capture-count")
def capture_count():
    try:
        return vision_service.capture_inventory()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/video_feed")
def video_feed():
    def generate():
        boundary = b"--frame\r\n"
        while True:
            frame = vision_service.get_latest_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            yield boundary
            yield b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/raw_feed")
def raw_feed():
    raise HTTPException(
        status_code=501,
        detail="Usa directamente la URL configurada de la ESP32-CAM para el stream sin anotar.",
    )
