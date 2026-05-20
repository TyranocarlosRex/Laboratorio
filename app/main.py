from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Mapping, Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import allowed_origins, check_runtime_config
from app.database import check_database_ready, execute_insert, get_db, init_db
from app.schemas import (
    AdminBootstrapCreate,
    AuthLoginRequest,
    AuthTokenResponse,
    MessageResponse,
    MovimientoCreate,
    MovimientoCreatedResponse,
    MovimientoResponse,
    MovimientoUpdate,
    SustanciaCreate,
    SustanciaResponse,
    SustanciaUpdate,
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
    normalize_movement_type,
    normalize_risk_level,
)
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Laboratorio API REST",
    description="Microservicio para gestionar sustancias y movimientos de inventario de laboratorio.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)
READ_ROLES = ("administrador", "responsable", "consultor")
WRITE_ROLES = ("administrador", "responsable")
ADMIN_ROLES = ("administrador",)


def _row_to_dict(row: Mapping[str, Any]) -> dict:
    return dict(row)


def _inventory_status(sustancia: dict) -> str:
    cantidad = float(sustancia["cantidad"])
    cantidad_minima = float(sustancia.get("cantidad_minima") or 0)
    cantidad_maxima = sustancia.get("cantidad_maxima")

    if cantidad < cantidad_minima:
        return "bajo"
    if cantidad_maxima is not None and cantidad > float(cantidad_maxima):
        return "excedido"
    return "normal"


def _sustancia_response(row: Mapping[str, Any]) -> dict:
    data = _row_to_dict(row)
    data["estado_inventario"] = _inventory_status(data)
    return data


def _get_sustancia_or_404(connection, sustancia_id: int) -> Mapping[str, Any]:
    row = connection.execute(
        "SELECT * FROM sustancias WHERE id = ?",
        (sustancia_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sustancia no encontrada",
        )
    return row


def _get_sustancia_for_update_or_404(
    connection,
    sustancia_id: int,
) -> Mapping[str, Any]:
    row = connection.execute(
        "SELECT * FROM sustancias WHERE id = ? FOR UPDATE",
        (sustancia_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sustancia no encontrada",
        )
    return row


def _get_movimiento_or_404(connection, movimiento_id: int) -> Mapping[str, Any]:
    row = connection.execute(
        "SELECT * FROM movimientos WHERE id = ?",
        (movimiento_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        )
    return row


def _get_movimiento_for_update_or_404(
    connection,
    movimiento_id: int,
) -> Mapping[str, Any]:
    row = connection.execute(
        "SELECT * FROM movimientos WHERE id = ? FOR UPDATE",
        (movimiento_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        )
    return row


def _get_usuario_or_404(connection, usuario_id: int) -> Mapping[str, Any]:
    row = connection.execute(
        "SELECT id, nombre, rol, created_at, updated_at FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return row


def _get_usuario_auth_by_nombre(
    connection,
    nombre: str,
) -> Mapping[str, Any] | None:
    return connection.execute(
        """
        SELECT id, nombre, contrasena, rol, created_at, updated_at
        FROM usuarios
        WHERE LOWER(nombre) = LOWER(?)
        """,
        (nombre,),
    ).fetchone()


def _get_usuario_public_by_id(connection, usuario_id: int) -> Mapping[str, Any] | None:
    return connection.execute(
        "SELECT id, nombre, rol, created_at, updated_at FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()


def _ensure_usuario_name_available(
    connection,
    nombre: str,
    current_user_id: int | None = None,
) -> None:
    row = connection.execute(
        "SELECT id FROM usuarios WHERE LOWER(nombre) = LOWER(?)",
        (nombre,),
    ).fetchone()

    if row is not None and row["id"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese nombre",
        )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Token de autenticacion requerido")

    try:
        payload = decode_access_token(credentials.credentials)
    except ExpiredSignatureError as error:
        raise _unauthorized("Token expirado") from error
    except InvalidTokenError as error:
        raise _unauthorized("Token invalido") from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    try:
        usuario_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as error:
        raise _unauthorized("Token invalido") from error

    with get_db() as connection:
        usuario = _get_usuario_public_by_id(connection, usuario_id)

    if usuario is None:
        raise _unauthorized("Usuario no encontrado")

    return _row_to_dict(usuario)


def require_roles(*allowed_roles: str):
    def dependency(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if current_user["rol"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta operacion",
            )
        return current_user

    return dependency


def _movement_delta(tipo: str, cantidad: float) -> float:
    return cantidad if tipo == "entrada" else -cantidad


def _lock_sustancias_for_update(connection, sustancia_ids: list[int]) -> None:
    for sustancia_id in sorted(set(sustancia_ids)):
        _get_sustancia_for_update_or_404(connection, sustancia_id)


def _update_sustancia_quantity(
    connection,
    sustancia_id: int,
    delta: float,
) -> Mapping[str, Any]:
    sustancia = _get_sustancia_for_update_or_404(connection, sustancia_id)
    nueva_cantidad = float(sustancia["cantidad"]) + delta

    if nueva_cantidad < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La operacion dejaria inventario negativo",
        )

    connection.execute(
        """
        UPDATE sustancias
        SET cantidad = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (nueva_cantidad, sustancia_id),
    )
    return _get_sustancia_or_404(connection, sustancia_id)


@app.get("/", tags=["Sistema"])
def root() -> dict:
    return {
        "mensaje": "Laboratorio API REST",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "login": "/auth/login",
    }


@app.get("/health", tags=["Sistema"])
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["Sistema"])
def readiness_check() -> dict:
    try:
        check_runtime_config()
        check_database_ready()
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from error

    return {"status": "ready", "database": "ok", "auth": "ok"}


@app.post(
    "/auth/bootstrap",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioResponse,
    tags=["Autenticacion"],
)
def bootstrap_admin(usuario: AdminBootstrapCreate) -> dict:
    with get_db() as connection:
        total_usuarios = connection.execute(
            "SELECT COUNT(*) AS total FROM usuarios"
        ).fetchone()["total"]

        if total_usuarios > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El administrador inicial ya fue configurado",
            )

        _ensure_usuario_name_available(connection, usuario.nombre)
        created_id = execute_insert(
            connection,
            """
            INSERT INTO usuarios (
                nombre,
                contrasena,
                rol,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'administrador', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (usuario.nombre, hash_password(usuario.contrasena)),
        )
        return _row_to_dict(_get_usuario_or_404(connection, created_id))


@app.post(
    "/auth/login",
    response_model=AuthTokenResponse,
    tags=["Autenticacion"],
)
def login_usuario(credentials: AuthLoginRequest) -> dict:
    with get_db() as connection:
        usuario = _get_usuario_auth_by_nombre(connection, credentials.nombre)

        if usuario is None or not verify_password(
            credentials.contrasena,
            usuario["contrasena"],
        ):
            raise _unauthorized("Credenciales invalidas")

        if password_needs_rehash(usuario["contrasena"]):
            connection.execute(
                """
                UPDATE usuarios
                SET contrasena = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (hash_password(credentials.contrasena), usuario["id"]),
            )

        public_usuario = _row_to_dict(_get_usuario_or_404(connection, usuario["id"]))

    try:
        access_token, expires_in = create_access_token(public_usuario)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "usuario": {
            "id": public_usuario["id"],
            "nombre": public_usuario["nombre"],
            "rol": public_usuario["rol"],
        },
    }


@app.get(
    "/sustancias/alertas",
    response_model=list[SustanciaResponse],
    tags=["Sustancias"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
def get_alertas_inventario() -> list[dict]:
    with get_db() as connection:
        rows = connection.execute("SELECT * FROM sustancias ORDER BY nombre").fetchall()
    return [
        _sustancia_response(row)
        for row in rows
        if _inventory_status(_row_to_dict(row)) in {"bajo", "excedido"}
    ]


@app.get(
    "/sustancias",
    response_model=list[SustanciaResponse],
    tags=["Sustancias"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
def get_sustancias(
    nombre: Annotated[str | None, Query(description="Busqueda parcial por nombre")] = None,
    categoria: Annotated[str | None, Query(description="Busqueda parcial por categoria")] = None,
    nivel_riesgo: Annotated[
        str | None, Query(description="Bajo, Medio o Alto")
    ] = None,
    estado: Annotated[
        str | None, Query(description="normal, bajo o excedido")
    ] = None,
) -> list[dict]:
    query = "SELECT * FROM sustancias"
    conditions: list[str] = []
    params: list[str] = []

    if nombre:
        conditions.append("LOWER(nombre) LIKE ?")
        params.append(f"%{nombre.strip().lower()}%")
    if categoria:
        conditions.append("LOWER(categoria) LIKE ?")
        params.append(f"%{categoria.strip().lower()}%")
    if nivel_riesgo:
        conditions.append("nivel_riesgo = ?")
        params.append(normalize_risk_level(nivel_riesgo))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY nombre"

    with get_db() as connection:
        rows = connection.execute(query, params).fetchall()

    response = [_sustancia_response(row) for row in rows]

    if estado:
        normalized_status = estado.strip().lower()
        if normalized_status not in {"normal", "bajo", "excedido"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="estado debe ser normal, bajo o excedido",
            )
        response = [
            sustancia
            for sustancia in response
            if sustancia["estado_inventario"] == normalized_status
        ]

    return response


@app.get(
    "/sustancias/{sustancia_id}",
    response_model=SustanciaResponse,
    tags=["Sustancias"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
def get_sustancia(sustancia_id: int) -> dict:
    with get_db() as connection:
        return _sustancia_response(_get_sustancia_or_404(connection, sustancia_id))


@app.post(
    "/sustancias",
    status_code=status.HTTP_201_CREATED,
    response_model=SustanciaResponse,
    tags=["Sustancias"],
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def create_sustancia(sustancia: SustanciaCreate) -> dict:
    with get_db() as connection:
        created_id = execute_insert(
            connection,
            """
            INSERT INTO sustancias (
                nombre,
                categoria,
                cantidad,
                unidad,
                nivel_riesgo,
                ubicacion,
                responsable,
                cantidad_minima,
                cantidad_maxima,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                sustancia.nombre,
                sustancia.categoria,
                sustancia.cantidad,
                sustancia.unidad,
                sustancia.nivel_riesgo,
                sustancia.ubicacion,
                sustancia.responsable,
                sustancia.cantidad_minima,
                sustancia.cantidad_maxima,
            ),
        )
        created = _get_sustancia_or_404(connection, created_id)
        return _sustancia_response(created)


@app.put(
    "/sustancias/{sustancia_id}",
    response_model=SustanciaResponse,
    tags=["Sustancias"],
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def update_sustancia(sustancia_id: int, sustancia: SustanciaUpdate) -> dict:
    with get_db() as connection:
        _get_sustancia_for_update_or_404(connection, sustancia_id)
        connection.execute(
            """
            UPDATE sustancias
            SET nombre = ?,
                categoria = ?,
                cantidad = ?,
                unidad = ?,
                nivel_riesgo = ?,
                ubicacion = ?,
                responsable = ?,
                cantidad_minima = ?,
                cantidad_maxima = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                sustancia.nombre,
                sustancia.categoria,
                sustancia.cantidad,
                sustancia.unidad,
                sustancia.nivel_riesgo,
                sustancia.ubicacion,
                sustancia.responsable,
                sustancia.cantidad_minima,
                sustancia.cantidad_maxima,
                sustancia_id,
            ),
        )
        updated = _get_sustancia_or_404(connection, sustancia_id)
        return _sustancia_response(updated)


@app.delete(
    "/sustancias/{sustancia_id}",
    response_model=MessageResponse,
    tags=["Sustancias"],
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def delete_sustancia(sustancia_id: int) -> dict:
    with get_db() as connection:
        _get_sustancia_for_update_or_404(connection, sustancia_id)
        movements_count = connection.execute(
            "SELECT COUNT(*) AS total FROM movimientos WHERE id_sustancia = ?",
            (sustancia_id,),
        ).fetchone()["total"]

        if movements_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede eliminar una sustancia con movimientos registrados",
            )

        connection.execute("DELETE FROM sustancias WHERE id = ?", (sustancia_id,))
        return {"mensaje": f"Sustancia {sustancia_id} eliminada"}


@app.get(
    "/movimientos",
    response_model=list[MovimientoResponse],
    tags=["Movimientos"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
def get_movimientos(
    id_sustancia: Annotated[int | None, Query(gt=0)] = None,
    tipo: Annotated[str | None, Query(description="entrada o salida")] = None,
) -> list[dict]:
    query = "SELECT * FROM movimientos"
    conditions: list[str] = []
    params: list[object] = []

    if id_sustancia is not None:
        conditions.append("id_sustancia = ?")
        params.append(id_sustancia)
    if tipo:
        conditions.append("tipo = ?")
        params.append(normalize_movement_type(tipo))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY fecha DESC, id DESC"

    with get_db() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


@app.get(
    "/movimientos/{movimiento_id}",
    response_model=MovimientoResponse,
    tags=["Movimientos"],
    dependencies=[Depends(require_roles(*READ_ROLES))],
)
def get_movimiento(movimiento_id: int) -> dict:
    with get_db() as connection:
        return _row_to_dict(_get_movimiento_or_404(connection, movimiento_id))


@app.post(
    "/movimientos",
    status_code=status.HTTP_201_CREATED,
    response_model=MovimientoCreatedResponse,
    tags=["Movimientos"],
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def create_movimiento(movimiento: MovimientoCreate) -> dict:
    with get_db() as connection:
        updated_sustancia = _update_sustancia_quantity(
            connection,
            movimiento.id_sustancia,
            _movement_delta(movimiento.tipo, movimiento.cantidad),
        )

        created_id = execute_insert(
            connection,
            """
            INSERT INTO movimientos (
                id_sustancia,
                tipo,
                cantidad,
                motivo,
                fecha
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                movimiento.id_sustancia,
                movimiento.tipo,
                movimiento.cantidad,
                movimiento.motivo,
            ),
        )

        created_movement = _get_movimiento_or_404(connection, created_id)

        return {
            "mensaje": "Movimiento registrado correctamente",
            "movimiento": _row_to_dict(created_movement),
            "sustancia": _sustancia_response(updated_sustancia),
        }


@app.put(
    "/movimientos/{movimiento_id}",
    response_model=MovimientoResponse,
    tags=["Movimientos"],
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def update_movimiento(movimiento_id: int, movimiento: MovimientoUpdate) -> dict:
    with get_db() as connection:
        old_movement = _get_movimiento_for_update_or_404(connection, movimiento_id)
        _lock_sustancias_for_update(
            connection,
            [old_movement["id_sustancia"], movimiento.id_sustancia],
        )

        old_delta = _movement_delta(
            old_movement["tipo"],
            float(old_movement["cantidad"]),
        )
        new_delta = _movement_delta(movimiento.tipo, movimiento.cantidad)

        if old_movement["id_sustancia"] == movimiento.id_sustancia:
            _update_sustancia_quantity(
                connection,
                movimiento.id_sustancia,
                new_delta - old_delta,
            )
        else:
            _update_sustancia_quantity(
                connection,
                old_movement["id_sustancia"],
                -old_delta,
            )
            _update_sustancia_quantity(
                connection,
                movimiento.id_sustancia,
                new_delta,
            )

        connection.execute(
            """
            UPDATE movimientos
            SET id_sustancia = ?,
                tipo = ?,
                cantidad = ?,
                motivo = ?
            WHERE id = ?
            """,
            (
                movimiento.id_sustancia,
                movimiento.tipo,
                movimiento.cantidad,
                movimiento.motivo,
                movimiento_id,
            ),
        )
        return _row_to_dict(_get_movimiento_or_404(connection, movimiento_id))


@app.delete(
    "/movimientos/{movimiento_id}",
    response_model=MessageResponse,
    tags=["Movimientos"],
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def delete_movimiento(movimiento_id: int) -> dict:
    with get_db() as connection:
        movimiento = _get_movimiento_for_update_or_404(connection, movimiento_id)
        _update_sustancia_quantity(
            connection,
            movimiento["id_sustancia"],
            -_movement_delta(movimiento["tipo"], float(movimiento["cantidad"])),
        )
        connection.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
        return {"mensaje": f"Movimiento {movimiento_id} eliminado"}


@app.get(
    "/usuarios",
    response_model=list[UsuarioResponse],
    tags=["Usuarios"],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
def get_usuarios() -> list[dict]:
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, nombre, rol, created_at, updated_at FROM usuarios ORDER BY nombre"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


@app.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResponse,
    tags=["Usuarios"],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
def get_usuario(usuario_id: int) -> dict:
    with get_db() as connection:
        return _row_to_dict(_get_usuario_or_404(connection, usuario_id))


@app.post(
    "/usuarios",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioResponse,
    tags=["Usuarios"],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
def create_usuario(usuario: UsuarioCreate) -> dict:
    with get_db() as connection:
        _ensure_usuario_name_available(connection, usuario.nombre)
        created_id = execute_insert(
            connection,
            """
            INSERT INTO usuarios (
                nombre,
                contrasena,
                rol,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (usuario.nombre, hash_password(usuario.contrasena), usuario.rol),
        )
        return _row_to_dict(_get_usuario_or_404(connection, created_id))


@app.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResponse,
    tags=["Usuarios"],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
def update_usuario(usuario_id: int, usuario: UsuarioUpdate) -> dict:
    with get_db() as connection:
        _get_usuario_or_404(connection, usuario_id)
        _ensure_usuario_name_available(connection, usuario.nombre, usuario_id)
        connection.execute(
            """
            UPDATE usuarios
            SET nombre = ?,
                contrasena = ?,
                rol = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                usuario.nombre,
                hash_password(usuario.contrasena),
                usuario.rol,
                usuario_id,
            ),
        )
        return _row_to_dict(_get_usuario_or_404(connection, usuario_id))


@app.delete(
    "/usuarios/{usuario_id}",
    response_model=MessageResponse,
    tags=["Usuarios"],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
)
def delete_usuario(usuario_id: int) -> dict:
    with get_db() as connection:
        _get_usuario_or_404(connection, usuario_id)
        connection.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        return {"mensaje": f"Usuario {usuario_id} eliminado"}
