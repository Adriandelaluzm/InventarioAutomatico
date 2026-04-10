# Inventario Automatico

Sistema de inventario con ESP32-CAM, YOLO, SQLite y dashboard web.

## Arquitectura

- `CameraWebServer/`: firmware para la ESP32-CAM AI Thinker.
- `app/`: backend FastAPI, persistencia SQLite y servicio de vision.
- `static/`: dashboard web.
- `best.pt`: modelo YOLO entrenado.
- `catalog.json`: relacion entre clase detectada y SKU.
- `.env.example`: configuracion base del sistema.

## Flujo

1. La ESP32-CAM publica el stream MJPEG.
2. El backend abre ese stream y corre YOLO para mostrar deteccion en vivo.
3. Desde la pagina web se presiona el boton de captura.
4. El backend analiza el frame actual y registra las detecciones en SQLite.
5. El dashboard muestra video anotado, inventario y detecciones recientes.

## Variables de entorno

- `ESP32_STREAM_URL`: URL del stream de la camara. Ejemplo: `http://192.168.1.11:81/stream`
- `MODEL_PATH`: ruta al modelo `best.pt`
- `DATABASE_PATH`: ruta del archivo SQLite
- `CATALOG_PATH`: ruta del catalogo SKU-clase
- `CONFIDENCE_THRESHOLD`: confianza minima de YOLO
- `FRAME_WIDTH` y `FRAME_HEIGHT`: resolucion interna de procesamiento
- `JPEG_QUALITY`: calidad JPEG del stream anotado que se manda al navegador
- `STREAM_BUFFER_SIZE`: buffer de lectura del stream para evitar que se acumulen frames viejos
- `MAX_INFERENCE_FPS`: limite de inferencias por segundo para priorizar fluidez sobre densidad de deteccion
- `API_HOST` y `API_PORT`: host y puerto del backend

## Configuracion inicial

1. Copia `.env.example` a `.env`.
2. Cambia `ESP32_STREAM_URL` por la IP real de tu ESP32-CAM.
3. Ajusta `catalog.json` si quieres cambiar SKUs o nombres.
4. Verifica que `best.pt` exista en la raiz del proyecto.

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecucion

```powershell
Copy-Item .env.example .env
notepad .env
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Abrir en el navegador:

- `http://127.0.0.1:8000/`

Tambien puedes usar:

```powershell
.\start_backend.ps1
```

o en `cmd`:

```bat
start_backend.bat
```

## Base de datos

Se crea automaticamente `inventario.db` con estas tablas:

- `products`
- `detections`
- `inventory`

## Flujo end-to-end

1. Flashea `CameraWebServer/` en la ESP32-CAM.
2. Enciende la ESP32-CAM y obten la IP desde el monitor serial.
3. Actualiza `ESP32_STREAM_URL` en `.env`.
4. Arranca el backend.
5. Abre `http://127.0.0.1:8000/`.
6. Coloca los objetos dentro de la vista de la camara.
7. Presiona `Capturar y contar` para registrar el inventario visible.

## Si cambia la red WiFi

Cuando cambia la red, normalmente cambian dos cosas:

- las credenciales WiFi guardadas en la ESP32-CAM
- la IP local de la camara

Sigue este proceso:

1. Abre `CameraWebServer/CameraWebServer.ino`.
2. Cambia las variables `ssid` y `password` por las credenciales de la nueva red.
3. Vuelve a flashear el firmware en la ESP32-CAM.
4. Abre el monitor serial del Arduino IDE.
5. Reinicia la ESP32-CAM y espera a que se conecte.
6. Copia la nueva IP que aparece en el mensaje `Camera Ready! Use 'http://<ip>' to connect`.
7. Abre el archivo `.env` en la raiz del proyecto.
8. Actualiza `ESP32_STREAM_URL` con la nueva IP.
9. Guarda `.env` y reinicia el backend.
10. Abre `http://127.0.0.1:8000/` y valida que el estado de vision cambie a `running`.

Ejemplo:

```env
ESP32_STREAM_URL=http://192.168.0.25:81/stream
```

Notas utiles:

- Si solo cambio la IP, no necesitas reentrenar el modelo ni cambiar `best.pt`.
- Si solo reiniciaste el router pero sigues en la misma red, igual conviene revisar la IP porque puede cambiar.
- Si el dashboard muestra `connecting` o `error`, revisa primero que la PC y la ESP32-CAM esten en la misma red.
- Las credenciales WiFi se cambian en `CameraWebServer/CameraWebServer.ino`, pero la URL del stream se cambia en `.env`.

## API principal

- `GET /api/health`
- `GET /api/settings`
- `GET /api/products`
- `GET /api/inventory`
- `GET /api/detections`
- `GET /api/vision/status`
- `POST /api/vision/start`
- `POST /api/vision/stop`
- `POST /api/inventory/reset`
- `POST /api/capture-count`
- `GET /video_feed`

