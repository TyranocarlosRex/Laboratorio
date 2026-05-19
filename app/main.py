from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from typing import Annotated, Mapping, Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.database import execute_insert, get_db, init_db
from app.schemas import (
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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


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


def _movement_delta(tipo: str, cantidad: float) -> float:
    return cantidad if tipo == "entrada" else -cantidad


def _update_sustancia_quantity(
    connection,
    sustancia_id: int,
    delta: float,
) -> Mapping[str, Any]:
    sustancia = _get_sustancia_or_404(connection, sustancia_id)
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
    }


@app.get("/health", tags=["Sistema"])
def health_check() -> dict:
    return {"status": "ok"}


@app.get(
    "/sustancias/alertas",
    response_model=list[SustanciaResponse],
    tags=["Sustancias"],
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
)
def get_sustancia(sustancia_id: int) -> dict:
    with get_db() as connection:
        return _sustancia_response(_get_sustancia_or_404(connection, sustancia_id))


@app.post(
    "/sustancias",
    status_code=status.HTTP_201_CREATED,
    response_model=SustanciaResponse,
    tags=["Sustancias"],
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
)
def update_sustancia(sustancia_id: int, sustancia: SustanciaUpdate) -> dict:
    with get_db() as connection:
        _get_sustancia_or_404(connection, sustancia_id)
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
)
def delete_sustancia(sustancia_id: int) -> dict:
    with get_db() as connection:
        _get_sustancia_or_404(connection, sustancia_id)
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
)
def get_movimiento(movimiento_id: int) -> dict:
    with get_db() as connection:
        return _row_to_dict(_get_movimiento_or_404(connection, movimiento_id))


@app.post(
    "/movimientos",
    status_code=status.HTTP_201_CREATED,
    response_model=MovimientoCreatedResponse,
    tags=["Movimientos"],
)
def create_movimiento(movimiento: MovimientoCreate) -> dict:
    with get_db() as connection:
        _get_sustancia_or_404(connection, movimiento.id_sustancia)

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
        updated_sustancia = _update_sustancia_quantity(
            connection,
            movimiento.id_sustancia,
            _movement_delta(movimiento.tipo, movimiento.cantidad),
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
)
def update_movimiento(movimiento_id: int, movimiento: MovimientoUpdate) -> dict:
    with get_db() as connection:
        old_movement = _get_movimiento_or_404(connection, movimiento_id)
        _get_sustancia_or_404(connection, movimiento.id_sustancia)

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
)
def delete_movimiento(movimiento_id: int) -> dict:
    with get_db() as connection:
        movimiento = _get_movimiento_or_404(connection, movimiento_id)
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
)
def get_usuario(usuario_id: int) -> dict:
    with get_db() as connection:
        return _row_to_dict(_get_usuario_or_404(connection, usuario_id))


@app.post(
    "/usuarios",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioResponse,
    tags=["Usuarios"],
)
def create_usuario(usuario: UsuarioCreate) -> dict:
    with get_db() as connection:
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
            (usuario.nombre, _hash_password(usuario.contrasena), usuario.rol),
        )
        return _row_to_dict(_get_usuario_or_404(connection, created_id))


@app.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResponse,
    tags=["Usuarios"],
)
def update_usuario(usuario_id: int, usuario: UsuarioUpdate) -> dict:
    with get_db() as connection:
        _get_usuario_or_404(connection, usuario_id)
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
                _hash_password(usuario.contrasena),
                usuario.rol,
                usuario_id,
            ),
        )
        return _row_to_dict(_get_usuario_or_404(connection, usuario_id))


@app.delete(
    "/usuarios/{usuario_id}",
    response_model=MessageResponse,
    tags=["Usuarios"],
)
def delete_usuario(usuario_id: int) -> dict:
    with get_db() as connection:
        _get_usuario_or_404(connection, usuario_id)
        connection.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        return {"mensaje": f"Usuario {usuario_id} eliminado"}
