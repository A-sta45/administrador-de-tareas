# Administrador de Tareas

Aplicación web hecha con **Flask** para gestionar tareas: login de usuarios, creación/edición de tareas y envío de recordatorios por **Telegram** cuando ocurre un evento sobre una tarea.

## Características

- Login de usuario y manejo de sesiones con Flask.
- Conexión a **MySQL** a través de `flask-mysqldb`, usando una conexión única (patrón **Singleton**).
- Notificaciones vía bot de Telegram implementadas con el patrón **Observer**: cada vez que ocurre un evento sobre una tarea, se notifica a los observadores suscritos (en este caso, `ChatBotObserver` envía un mensaje al chat configurado).
- Interfaz en HTML/CSS (carpetas `templates/` y `static/`).

## Estructura

- `app.py` — app Flask, conexión a MySQL y lógica de notificaciones a Telegram.
- `templates/`, `static/` — vistas e interfaz.
- `tests/` — pruebas con `pytest`.

## Configuración local

Este proyecto necesita dos archivos que **no se suben a GitHub** (están en `.gitignore`) porque contienen datos sensibles:

**`config.py`** (en la raíz del proyecto):

```python
HEX_SEC_KEY = "una_clave_secreta_para_las_sesiones_de_flask"
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_DB = "nombre_de_tu_base_de_datos"
```

**`.env`** (en la raíz del proyecto), con el token del bot de Telegram:

```
TELEGRAM_BOT_TOKEN=tu_token_del_bot
```

El token se obtiene creando un bot con [@BotFather](https://t.me/BotFather) en Telegram. También falta configurar el `chat_id` del destinatario en `app.py` (`ChatBotObserver.chat_id`).

## Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Tests

```bash
pytest
```
