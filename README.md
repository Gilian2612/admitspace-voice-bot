# Zepur Voice Bot — AdmitSpace / Tennessee Tech

Bot de voz en tiempo real. Backend Python + WebSocket. Frontend HTML puro.

---

## Setup (primera vez)

```bash
# 1. Clonar / descomprimir el proyecto
cd zepur-voicebot

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Llenar las keys en .env
#    Edita el archivo .env con tus API keys reales
```

---

## Correr el servidor

```bash
uvicorn main:app --reload --port 8000
```

Luego abre `index.html` directamente en el navegador (doble clic).

---

## Demo remota con ngrok (otro PC, otra red)

```bash
# Instalar ngrok: https://ngrok.com/download
ngrok http 8000
```

Ngrok te da una URL como:
```
https://a3f2-190-xxx.ngrok.io
```

Abre `index.html` y cambia esta línea:
```js
const WS_URL = "wss://a3f2-190-xxx.ngrok.io/ws";
```

Mándale el `index.html` modificado a Zepur. El token `zepur2025` ya está incluido.

---

## Archivos

| Archivo          | Qué hace                                      |
|------------------|-----------------------------------------------|
| `main.py`        | Backend FastAPI: WebSocket, Whisper, Claude, ElevenLabs |
| `index.html`     | Frontend: micrófono, chat, reproducción de audio |
| `.env`           | API keys (nunca subir a git)                  |
| `requirements.txt` | Dependencias Python                         |

---

## Seguridad

El WebSocket valida el token antes de aceptar la conexión.
Cualquier cliente sin `?token=zepur2025` recibe cierre inmediato (code 1008).

Para producción: cambiar el token, agregar HTTPS propio, limitar CORS.

---

## Cambiar la voz (ElevenLabs)

Edita `ELEVENLABS_VOICE_ID` en `.env`.
Voces gratuitas disponibles en: https://elevenlabs.io/voice-library
