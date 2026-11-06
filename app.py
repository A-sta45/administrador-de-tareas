# ----------------------------------------------
# Importación de librerías necesarias para Flask
# ----------------------------------------------
import os
from flask import Flask, render_template, request, session, redirect, url_for
import config  # Archivo de configuración (host, user, pass, keys)
from datetime import datetime  # Para generar fecha/hora actual de tareas
import requests  # Para realizar peticiones HTTP (Telegram Bot API)

# ----------------------------------------------------
# Crear la instancia principal de la aplicación Flask
# ----------------------------------------------------
app = Flask(__name__)


# ----------------------------------------------------
# Configurar valores de seguridad y conexión a MySQL
# ----------------------------------------------------
app.config["SECRET_KEY"] = config.HEX_SEC_KEY  # Llave para manejo de sesiones
app.config["MYSQL_HOST"] = config.MYSQL_HOST  # Host del servidor MySQL
app.config["MYSQL_USER"] = config.MYSQL_USER  # Usuario de MySQL
app.config["MYSQL_PASSWORD"] = config.MYSQL_PASSWORD  # Password del usuario MySQL
app.config["MYSQL_DB"] = config.MYSQL_DB  # Base de datos a utilizar


# =========================================================
#           PATRÓN DE DISEÑO: SINGLETON (MySQL)
# =========================================================
# Esta clase garantiza que exista SOLO una instancia de conexión
# MySQL en toda la aplicación Flask. Evita múltiples conexiones
# innecesarias y optimiza recursos.
class MySQLSingleton:
    _instance = None  # Variable de clase donde se almacenará la instancia única

    def __new__(cls, app=None):
        """
        Método especial __new__ se ejecuta antes del constructor.
        Se usa para controlar la creación de instancias.
        """
        if cls._instance is None:
            # Importar dentro del método evita que cargue antes de tiempo
            from flask_mysqldb import MySQL

            # Crear instancia
            cls._instance = super(MySQLSingleton, cls).__new__(cls)
            cls._instance.mysql = MySQL(app)  # Conexión MySQL asociada a la app Flask

        return cls._instance  # Siempre devuelve la misma instancia

    def get_connection(self):
        """Retorna el objeto de conexión MySQL para ejecutar consultas."""
        return self.mysql.connection


# Crear una instancia única de MySQL para toda la aplicación
mysql_singleton = MySQLSingleton(app)
mysql = mysql_singleton.mysql


# =========================================================
#              PATRÓN DE DISEÑO: OBSERVER
# =========================================================
# El patrón Observer permite que un objeto “emita eventos”
# y que otros objetos (observadores) reciban notificaciones.
# Aquí se usa para avisar al bot de Telegram cuando se crea una tarea.
# =========================================================


# -------------------------------
# Clase base SUJETO (Subject)
# -------------------------------
class Subject:
    def __init__(self):
        self._observers = []  # Lista de objetos observadores

    def register(self, observer):
        """Registra un observador que escuchará los eventos."""
        self._observers.append(observer)

    def notify(self, message):
        """
        Envía un mensaje a todos los observadores.
        Se ejecuta cuando ocurre un evento en el sistema.
        """
        for observer in self._observers:
            observer.update(message)


# ---------------------------------------------------------------
# Observador concreto: envía mensajes a Telegram cuando es notificado
# ---------------------------------------------------------------
class ChatBotObserver:
    def __init__(self):
        # Token del bot de Telegram (configurar con la variable de entorno TELEGRAM_BOT_TOKEN)
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

        # ID del chat donde se enviarán los mensajes
        self.chat_id = 0000000

    def update(self, message):
        """Envía un mensaje al bot de Telegram usando su API."""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}

        try:
            response = requests.post(url, data=payload)
            if not response.ok:
                print(f"Error enviando mensaje Telegram: {response.text}")
        except Exception as e:
            print(f"Excepción enviando mensaje Telegram: {e}")


# ------------------------------------------------------------
# Clase concreta sujeto: encargado de gestionar eventos de tareas
# ------------------------------------------------------------
class TaskManager(Subject):
    def new_task(self, task_data):
        """
        MÉTODO QUE DISPARA EL EVENTO:
        Cuando se crea una nueva tarea, se notifica a los observadores.
        """
        self.notify(f"Nueva tarea creada: {task_data['title']}")


# Instanciar el manejador de tareas (sujeto)
task_manager = TaskManager()

# Instanciar el observador (Telegram bot)
chatbot = ChatBotObserver()

# Registrar al observador en el sujeto
task_manager.register(chatbot)


# =========================================================
#                      RUTAS FLASK
# =========================================================


# ---------------------------
# Ruta principal (login)
# ---------------------------
@app.route("/", methods=["GET"])
def home():
    """Muestra la página inicial de login."""
    return render_template("index.html")


# ---------------------------
# Ruta de login POST
# ---------------------------
@app.route("/login", methods=["POST"])
def login():
    """Procesa el formulario de login y valida credenciales."""

    email = request.form["email"]
    password = request.form["password"]

    # Obtener conexión MySQL
    conn = mysql_singleton.get_connection()
    cur = conn.cursor()

    # Ejecutar consulta verificando email y password
    cur.execute(
        "SELECT * FROM users WHERE email = %s AND password = %s", (email, password)
    )
    user = cur.fetchone()
    cur.close()

    # Si el usuario existe → crear sesión
    if user is not None:
        session["email"] = email
        session["name"] = user[1]  # Columna nombre
        session["surnames"] = user[2]  # Columna apellidos
        return redirect(url_for("tasks"))

    # Si las credenciales fallan → mostrar error
    return render_template("index.html", message="Las credenciales no son correctas")


# -------------------------------------------
# Pantalla de tareas del usuario autenticado
# -------------------------------------------
@app.route("/tasks", methods=["GET"])
def tasks():
    """Muestra todas las tareas del usuario logueado."""

    # Validación de sesión
    if "email" not in session:
        return redirect(url_for("home"))

    email = session["email"]

    conn = mysql_singleton.get_connection()
    cur = conn.cursor()

    # Obtener todas las tareas asociadas al email
    cur.execute("SELECT * FROM tasks WHERE email = %s", [email])
    rows = cur.fetchall()

    # Obtener nombres de columnas para convertir a diccionarios
    columnNames = [col[0] for col in cur.description]
    data = [dict(zip(columnNames, r)) for r in rows]

    cur.close()

    # Renderizar tabla de tareas
    return render_template("tasks.html", tasks=data)


# ----------------
# Cerrar sesión
# ----------------
@app.route("/logout")
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    return redirect(url_for("home"))


# ---------------------------------------
# Crear nueva tarea (POST)
# ---------------------------------------
@app.route("/new-task", methods=["POST"])
def newTask():
    """Crea una nueva tarea y notifica al bot de Telegram."""

    if "email" not in session:
        return redirect(url_for("home"))

    title = request.form["title"]
    description = request.form["description"]
    email = session["email"]

    # Generar fecha actual en formato estándar
    d = datetime.now()
    dateTask = d.strftime("%Y-%m-%d %H:%M:%S")

    # Validación de campos
    if title and description and email:
        conn = mysql_singleton.get_connection()
        cur = conn.cursor()

        # Insertar nueva tarea en la BD
        sql = "INSERT INTO tasks (email, title, description, date_task) VALUES (%s, %s, %s, %s)"
        cur.execute(sql, (email, title, description, dateTask))
        conn.commit()
        cur.close()

        # Notificar al Observer → Telegram
        task_manager.new_task({"title": title, "description": description})

    return redirect(url_for("tasks"))


# ----------------------------------------
# Registro de nuevo usuario
# ----------------------------------------
@app.route("/new-user", methods=["POST"])
def newUser():
    """Crea un nuevo usuario en la base de datos."""

    name = request.form["name"]
    surnames = request.form["surnames"]
    email = request.form["email"]
    password = request.form["password"]
    telefono = request.form["telefono"]  # Nuevo campo

    # Validar todos los campos
    if name and surnames and email and password and telefono:
        conn = mysql_singleton.get_connection()
        cur = conn.cursor()

        sql = "INSERT INTO users (name, surnames, email, password, telefono) VALUES (%s, %s, %s, %s, %s)"
        cur.execute(sql, (name, surnames, email, password, telefono))
        conn.commit()
        cur.close()

    return redirect(url_for("tasks"))


# ---------------------------------------------
# Eliminar tarea por ID (POST)
# ---------------------------------------------
@app.route("/delete-task", methods=["POST"])
def deleteTask():
    """Elimina una tarea específica de la base de datos."""

    if "email" not in session:
        return redirect(url_for("home"))

    conn = mysql_singleton.get_connection()
    cur = conn.cursor()

    id = request.form["id"]  # ID de la tarea a eliminar

    cur.execute("DELETE FROM tasks WHERE id = %s", (id,))
    conn.commit()
    cur.close()

    return redirect(url_for("tasks"))


# ---------------------------------------------
# Inicialización del servidor Flask
# ---------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)  # Modo debug activado
