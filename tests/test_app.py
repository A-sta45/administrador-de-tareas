# ============================================
# TESTS DOCUMENTADOS PARA LA APP FLASK DE TAREAS
# ============================================


def test_home_page_muestra_login(client):
    """
    Verifica que la página principal ("/") muestre el formulario de login.

    GIVEN:
        - La aplicación está en modo de pruebas.

    WHEN:
        - Se realiza una petición GET a "/".

    THEN:
        - La respuesta debe ser 200 (OK).
        - El contenido debe incluir elementos asociados al login,
          como el texto "Login" o el campo "email".
    """
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Login" in resp.data or b"email" in resp.data


def test_login_invalido(client, patch_mysql):
    """
    Verifica que un intento de login con credenciales inválidas
    muestre el mensaje de error adecuado.

    GIVEN:
        - La base de datos no contiene el usuario (mock con patch_mysql).

    WHEN:
        - Se envía un POST a '/login' con credenciales incorrectas.

    THEN:
        - La respuesta debe ser 200 (se recarga la pantalla de login).
        - Debe mostrarse el mensaje:
          "Las credenciales no son correctas".
    """
    patch_mysql(script_dict={("users", ("fake@test.com", "wrong")): None})

    resp = client.post("/login", data={"email": "fake@test.com", "password": "wrong"})

    assert resp.status_code == 200
    assert b"Las credenciales no son correctas" in resp.data


def test_login_exitoso_redirige_a_tasks(client, patch_mysql):
    """
    Verifica que un login exitoso redirija a la página de tareas (/tasks).

    GIVEN:
        - Un usuario válido existe en la base de datos (mock con patch_mysql).

    WHEN:
        - Se hace un POST a "/login" con credenciales correctas.

    THEN:
        - La respuesta debe ser una redirección (302).
        - El destino debe ser "/tasks".
    """
    patch_mysql(
        script_dict={
            ("users", ("juan@test.com", "1234")): (
                1,
                "Juan",
                "Perez",
                "juan@test.com",
                "1234",
            )
        }
    )

    resp = client.post("/login", data={"email": "juan@test.com", "password": "1234"})

    assert resp.status_code == 302
    assert "/tasks" in resp.headers["Location"]


def test_tasks_redirige_si_no_hay_login(client):
    """
    Verifica que la ruta /tasks no sea accesible sin estar autenticado.

    GIVEN:
        - No existe una sesión activa.

    WHEN:
        - Se realiza un GET a "/tasks".

    THEN:
        - La respuesta debe ser una redirección (302).
        - Debe redirigir a la página principal ("/").
    """
    resp = client.get("/tasks", follow_redirects=False)

    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_tasks_lista_muestra_titulos(client, patch_mysql):
    """
    Verifica que la lista de tareas muestre correctamente las tareas
    obtenidas desde la base de datos.

    GIVEN:
        - La sesión está iniciada (se configura el email en session).
        - La base de datos retorna dos tareas para ese usuario (mock con patch_mysql).

    WHEN:
        - Se hace un GET a "/tasks".

    THEN:
        - La respuesta debe ser 200 (OK).
        - El contenido HTML debe mostrar los títulos de las tareas:
            * "Pagar servicios"
            * "Comprar leche"
    """
    # Simular sesión iniciada
    with client.session_transaction() as sess:
        sess["email"] = "juan@test.com"

    # Simular BD con dos tareas
    patch_mysql(
        script_dict={
            ("tasks", ("juan@test.com",)): [
                (
                    1,
                    "juan@test.com",
                    "Pagar servicios",
                    "Luz/agua",
                    "2025-09-25 10:00:00",
                ),
                (
                    2,
                    "juan@test.com",
                    "Comprar leche",
                    "1L descremada",
                    "2025-09-25 12:00:00",
                ),
            ]
        }
    )

    resp = client.get("/tasks")

    assert resp.status_code == 200
    assert b"Pagar servicios" in resp.data
    assert b"Comprar leche" in resp.data
