# ============================================================
# conftest.py — Configuración de pruebas y mocks de MySQL
# ============================================================

import pytest
from app import app as flask_app


# ============================================================
# FIXTURES BASE PARA EJECUTAR LA APP FLASK EN MODO TEST
# ============================================================


@pytest.fixture
def app():
    """
    Fixture que prepara la aplicación Flask para ser usada en los tests.

    - TESTING=True               → Activa modo prueba (desactiva errores HTML).
    - WTF_CSRF_ENABLED=False     → Permite enviar formularios sin token CSRF.
    - SECRET_KEY                 → Clave simple para manejo de sesiones.

    El fixture retorna la aplicación configurada mediante yield.
    """
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="testkey",
    )
    yield flask_app


@pytest.fixture
def client(app):
    """
    Devuelve un test_client() de Flask.

    Este objeto permite simular:
        - GET
        - POST
        - Cookies
        - Sesiones
        - Redirecciones

    Se usa en todos los tests que necesitan hacer peticiones a la app.
    """
    return app.test_client()


# ============================================================
# CLASES DUMMY PARA SIMULAR EL COMPORTAMIENTO DE MYSQL
# ============================================================


class DummyCursor:
    """
    Cursor falso que simula las operaciones SELECT de MySQL.

    - Guarda el último query ejecutado.
    - Devuelve resultados personalizados según el script de prueba.
    - Emula fetchone() y fetchall() dependiendo de la tabla consultada.
    """

    def __init__(self, script=None):
        # script es un diccionario que define qué debe devolver la BD simulada
        self._script = script or {}
        self.description = None  # Usado cuando Flask/Jinja necesita nombres de columnas
        self._last_query = None
        self._conn = None  # Esta propiedad será asignada por DummyConnection

    def execute(self, q, params=None):
        """
        Guarda la última consulta SQL y define columnas simuladas
        para consultas sobre la tabla 'tasks'.
        """
        self._last_query = (q, tuple(params) if params else tuple())

        if "FROM tasks" in q:
            # Describe columnas como haría MySQL
            self.description = (
                ("id",),
                ("email",),
                ("title",),
                ("description",),
                ("date_task",),
            )
        else:
            self.description = None

    def fetchone(self):
        """
        Devuelve un único registro simulado.

        Usado para:
            SELECT * FROM users WHERE email=%s AND password=%s
        """
        q, p = self._last_query
        if "FROM users" in q:
            return self._script.get(("users", p), None)
        return None

    def fetchall(self):
        """
        Devuelve múltiples registros simulados.

        Usado para:
            SELECT * FROM tasks WHERE email=%s
        """
        q, p = self._last_query
        if "FROM tasks" in q:
            return self._script.get(("tasks", p), [])
        return []

    def close(self):
        """Método vacío porque en el mock no es necesario cerrar nada."""
        pass


class DummyConnection:
    """
    Conexión falsa de MySQL.

    - Devuelve el DummyCursor asociado.
    - Cuenta commit() para pruebas que lo requieran.
    """

    def __init__(self, cursor_obj):
        self._cursor_obj = cursor_obj
        self.commits = 0
        cursor_obj._conn = self  # Permite que el cursor acceda a esta conexión

    def cursor(self):
        return self._cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


class DummyMySQL:
    """
    Objeto que imita a mysql.connector.connect().

    Guarda internamente una DummyConnection.
    """

    def __init__(self, cursor_obj):
        self.connection = DummyConnection(cursor_obj)


# ============================================================
# FIXTURE PRINCIPAL PARA PARCHEAR EL SINGLETON MYSQL
# ============================================================


@pytest.fixture
def patch_mysql(monkeypatch):
    """
    Parchea la instancia existente de mysql_singleton.mysql en app.py.

    Uso en tests:
        patch_mysql({
            ("users", ("email@test.com", "pass")): (...fila...)
        })

    El diccionario debe tener claves de la forma:
        ("users", (param1, param2))
        ("tasks", (email,))

    Y valores que correspondan al resultado esperado:
        - None
        - Una tupla (para fetchone)
        - Una lista de tuplas (para fetchall)
    """

    import app as app_module  # Importa el módulo para modificar su singleton

    def _set_script(script_dict):
        """
        script_dict = { (("tabla"), (parámetros)): resultado }

        Crea un DummyCursor con ese script y reemplaza el MySQL real
        por uno falso antes del test.
        """
        dummy_cursor = DummyCursor(script=script_dict)
        dummy_mysql = DummyMySQL(dummy_cursor)

        # Se reemplaza la instancia mysql_singleton.mysql del app
        monkeypatch.setattr(app_module.mysql_singleton, "mysql", dummy_mysql)

        return dummy_cursor

    return _set_script
