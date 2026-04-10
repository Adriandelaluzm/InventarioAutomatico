from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
YOLO_CONFIG_DIR = BASE_DIR / ".ultralytics"

os.environ.setdefault("YOLO_CONFIG_DIR", str(YOLO_CONFIG_DIR))


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    model_path: Path = Path(os.getenv("MODEL_PATH", BASE_DIR / "best.pt"))
    esp32_stream_url: str = os.getenv("ESP32_STREAM_URL", "http://192.168.1.11:81/stream")
    database_path: Path = Path(os.getenv("DATABASE_PATH", BASE_DIR / "inventario.db"))
    catalog_path: Path = Path(os.getenv("CATALOG_PATH", BASE_DIR / "catalog.json"))
    line_y: int = int(os.getenv("LINE_Y", "300"))
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))
    frame_width: int = int(os.getenv("FRAME_WIDTH", "960"))
    frame_height: int = int(os.getenv("FRAME_HEIGHT", "540"))
    jpeg_quality: int = int(os.getenv("JPEG_QUALITY", "80"))
    stream_buffer_size: int = int(os.getenv("STREAM_BUFFER_SIZE", "1"))
    max_inference_fps: float = float(os.getenv("MAX_INFERENCE_FPS", "6"))
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
