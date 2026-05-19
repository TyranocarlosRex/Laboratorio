import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 5


def mostrar_respuesta(response):
    print(f"\nEstado HTTP: {response.status_code}")
    try:
        print(response.json())
    except requests.exceptions.JSONDecodeError:
        cuerpo = response.text.strip()
        print(cuerpo if cuerpo else "La respuesta esta vacia o no es JSON.")


def realizar_peticion(method, endpoint, **kwargs):
    try:
        response = requests.request(
            method,
            f"{BASE_URL}{endpoint}",
            timeout=TIMEOUT,
            **kwargs,
        )
        mostrar_respuesta(response)
    except requests.exceptions.RequestException as error:
        print(f"No se pudo conectar con la API: {error}")


def leer_entero(mensaje):
    try:
        return int(input(mensaje))
    except ValueError:
        print("Debe ingresar un numero entero.")
        return None


def leer_flotante(mensaje):
    try:
        return float(input(mensaje))
    except ValueError:
        print("Debe ingresar un numero valido.")
        return None


# =========================
# SUSTANCIAS
# =========================
def get_sustancias():
    realizar_peticion("GET", "/sustancias")


def get_sustancia():
    sustancia_id = leer_entero("Ingrese el ID de la sustancia: ")
    if sustancia_id is None:
        return
    realizar_peticion("GET", f"/sustancias/{sustancia_id}")


def create_sustancia():
    nombre = input("Ingrese el nombre: ")
    categoria = input("Ingrese la categoria: ")
    cantidad = leer_flotante("Ingrese la cantidad: ")
    if cantidad is None:
        return
    unidad = input("Ingrese la unidad: ")
    nivel_riesgo = input("Ingrese el nivel de riesgo: ")
    ubicacion = input("Ingrese la ubicacion: ")
    responsable = input("Ingrese el responsable: ")

    payload = {
        "nombre": nombre,
        "categoria": categoria,
        "cantidad": cantidad,
        "unidad": unidad,
        "nivel_riesgo": nivel_riesgo,
        "ubicacion": ubicacion,
        "responsable": responsable,
    }

    realizar_peticion("POST", "/sustancias", json=payload)


def update_sustancia():
    sustancia_id = leer_entero("Ingrese el ID de la sustancia a actualizar: ")
    if sustancia_id is None:
        return

    nombre = input("Ingrese el nuevo nombre: ")
    categoria = input("Ingrese la nueva categoria: ")
    cantidad = leer_flotante("Ingrese la nueva cantidad: ")
    if cantidad is None:
        return
    unidad = input("Ingrese la nueva unidad: ")
    nivel_riesgo = input("Ingrese el nuevo nivel de riesgo: ")
    ubicacion = input("Ingrese la nueva ubicacion: ")
    responsable = input("Ingrese el nuevo responsable: ")

    payload = {
        "nombre": nombre,
        "categoria": categoria,
        "cantidad": cantidad,
        "unidad": unidad,
        "nivel_riesgo": nivel_riesgo,
        "ubicacion": ubicacion,
        "responsable": responsable,
    }

    realizar_peticion("PUT", f"/sustancias/{sustancia_id}", json=payload)


def delete_sustancia():
    sustancia_id = leer_entero("Ingrese el ID de la sustancia a eliminar: ")
    if sustancia_id is None:
        return
    realizar_peticion("DELETE", f"/sustancias/{sustancia_id}")


# =========================
# MOVIMIENTOS
# =========================
def get_movimientos():
    realizar_peticion("GET", "/movimientos")


def get_movimiento():
    movimiento_id = leer_entero("Ingrese el ID del movimiento: ")
    if movimiento_id is None:
        return
    realizar_peticion("GET", f"/movimientos/{movimiento_id}")


def create_movimiento():
    id_sustancia = leer_entero("Ingrese el ID de la sustancia: ")
    if id_sustancia is None:
        return

    tipo = input("Ingrese el tipo (entrada/salida): ").strip().lower()
    cantidad = leer_flotante("Ingrese la cantidad: ")
    if cantidad is None:
        return
    motivo = input("Ingrese el motivo: ")

    payload = {
        "id_sustancia": id_sustancia,
        "tipo": tipo,
        "cantidad": cantidad,
        "motivo": motivo,
    }

    realizar_peticion("POST", "/movimientos", json=payload)


def update_movimiento():
    movimiento_id = leer_entero("Ingrese el ID del movimiento a actualizar: ")
    if movimiento_id is None:
        return

    id_sustancia = leer_entero("Ingrese el ID de la sustancia: ")
    if id_sustancia is None:
        return

    tipo = input("Ingrese el tipo (entrada/salida): ").strip().lower()
    cantidad = leer_flotante("Ingrese la cantidad: ")
    if cantidad is None:
        return
    motivo = input("Ingrese el motivo: ")

    payload = {
        "id_sustancia": id_sustancia,
        "tipo": tipo,
        "cantidad": cantidad,
        "motivo": motivo,
    }

    realizar_peticion("PUT", f"/movimientos/{movimiento_id}", json=payload)


def delete_movimiento():
    movimiento_id = leer_entero("Ingrese el ID del movimiento a eliminar: ")
    if movimiento_id is None:
        return
    realizar_peticion("DELETE", f"/movimientos/{movimiento_id}")


# =========================
# USUARIOS
# =========================
def get_usuarios():
    realizar_peticion("GET", "/usuarios")


def get_usuario():
    usuario_id = leer_entero("Ingrese el ID del usuario: ")
    if usuario_id is None:
        return
    realizar_peticion("GET", f"/usuarios/{usuario_id}")


def create_usuario():
    nombre = input("Ingrese el nombre: ")
    contrasena = input("Ingrese la contrasena: ")
    rol = input("Ingrese el rol: ")

    payload = {
        "nombre": nombre,
        "contrasena": contrasena,
        "rol": rol,
    }

    realizar_peticion("POST", "/usuarios", json=payload)


def update_usuario():
    usuario_id = leer_entero("Ingrese el ID del usuario a actualizar: ")
    if usuario_id is None:
        return

    nombre = input("Ingrese el nuevo nombre: ")
    contrasena = input("Ingrese la nueva contrasena: ")
    rol = input("Ingrese el nuevo rol: ")

    payload = {
        "nombre": nombre,
        "contrasena": contrasena,
        "rol": rol,
    }

    realizar_peticion("PUT", f"/usuarios/{usuario_id}", json=payload)


def delete_usuario():
    usuario_id = leer_entero("Ingrese el ID del usuario a eliminar: ")
    if usuario_id is None:
        return
    realizar_peticion("DELETE", f"/usuarios/{usuario_id}")


# =========================
# MENU
# =========================
def menu():
    while True:
        print("\n--- MENU PRINCIPAL ---")
        print("1. Ver todas las sustancias")
        print("2. Ver una sustancia por ID")
        print("3. Crear una sustancia")
        print("4. Actualizar una sustancia")
        print("5. Eliminar una sustancia")
        print("6. Ver todos los movimientos")
        print("7. Ver un movimiento por ID")
        print("8. Crear un movimiento")
        print("9. Actualizar un movimiento")
        print("10. Eliminar un movimiento")
        print("11. Ver todos los usuarios")
        print("12. Ver un usuario por ID")
        print("13. Crear un usuario")
        print("14. Actualizar un usuario")
        print("15. Eliminar un usuario")
        print("16. Salir")

        opcion = input("Seleccione una opcion: ")

        if opcion == "1":
            get_sustancias()
        elif opcion == "2":
            get_sustancia()
        elif opcion == "3":
            create_sustancia()
        elif opcion == "4":
            update_sustancia()
        elif opcion == "5":
            delete_sustancia()
        elif opcion == "6":
            get_movimientos()
        elif opcion == "7":
            get_movimiento()
        elif opcion == "8":
            create_movimiento()
        elif opcion == "9":
            update_movimiento()
        elif opcion == "10":
            delete_movimiento()
        elif opcion == "11":
            get_usuarios()
        elif opcion == "12":
            get_usuario()
        elif opcion == "13":
            create_usuario()
        elif opcion == "14":
            update_usuario()
        elif opcion == "15":
            delete_usuario()
        elif opcion == "16":
            print("Saliendo del programa...")
            break
        else:
            print("Opcion invalida, intente de nuevo.")


if __name__ == "__main__":
    menu()
