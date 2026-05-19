from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


VALID_RISK_LEVELS = {
    "bajo": "Bajo",
    "medio": "Medio",
    "alto": "Alto",
}
VALID_ROLES = {"administrador", "responsable", "consultor"}
VALID_MOVEMENT_TYPES = {"entrada", "salida"}


def normalize_risk_level(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_RISK_LEVELS:
        raise ValueError("nivel_riesgo debe ser Bajo, Medio o Alto")
    return VALID_RISK_LEVELS[normalized]


def normalize_role(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_ROLES:
        raise ValueError("rol debe ser administrador, responsable o consultor")
    return normalized


def normalize_movement_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_MOVEMENT_TYPES:
        raise ValueError("tipo debe ser entrada o salida")
    return normalized


class SustanciaBase(BaseModel):
    nombre: str = Field(..., min_length=1, examples=["Acido clorhidrico"])
    categoria: str = Field(..., min_length=1, examples=["Acido"])
    cantidad: float = Field(..., ge=0, examples=[5])
    unidad: str = Field(..., min_length=1, examples=["litros"])
    nivel_riesgo: str = Field(..., examples=["Alto"])
    ubicacion: str = Field(..., min_length=1, examples=["Estante A-2"])
    responsable: str = Field(..., min_length=1, examples=["Encargado de laboratorio"])
    cantidad_minima: float = Field(default=0, ge=0, examples=[1])
    cantidad_maxima: float | None = Field(default=None, ge=0, examples=[20])

    @field_validator("nombre", "categoria", "unidad", "ubicacion", "responsable")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("el campo no puede estar vacio")
        return value

    @field_validator("nivel_riesgo")
    @classmethod
    def validate_risk_level(cls, value: str) -> str:
        return normalize_risk_level(value)

    @model_validator(mode="after")
    def validate_limits(self) -> "SustanciaBase":
        if self.cantidad_maxima is not None and self.cantidad_maxima < self.cantidad_minima:
            raise ValueError("cantidad_maxima no puede ser menor que cantidad_minima")
        return self


class SustanciaCreate(SustanciaBase):
    pass


class SustanciaUpdate(SustanciaBase):
    pass


class SustanciaResponse(SustanciaBase):
    id: int
    estado_inventario: Literal["normal", "bajo", "excedido"]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MovimientoBase(BaseModel):
    id_sustancia: int = Field(..., gt=0, examples=[1])
    tipo: str = Field(..., examples=["entrada"])
    cantidad: float = Field(..., gt=0, examples=[2])
    motivo: str = Field(..., min_length=1, examples=["Reposicion de inventario"])

    @field_validator("tipo")
    @classmethod
    def validate_movement_type(cls, value: str) -> str:
        return normalize_movement_type(value)

    @field_validator("motivo")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("motivo no puede estar vacio")
        return value


class MovimientoCreate(MovimientoBase):
    pass


class MovimientoUpdate(MovimientoBase):
    pass


class MovimientoResponse(MovimientoBase):
    id: int
    fecha: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MovimientoCreatedResponse(BaseModel):
    mensaje: str
    movimiento: MovimientoResponse
    sustancia: SustanciaResponse


class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=1, examples=["Carlos Cordova"])
    rol: str = Field(..., examples=["responsable"])

    @field_validator("nombre")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("nombre no puede estar vacio")
        return value

    @field_validator("rol")
    @classmethod
    def validate_role(cls, value: str) -> str:
        return normalize_role(value)


class UsuarioCreate(UsuarioBase):
    contrasena: str = Field(..., min_length=4, examples=["123456"])


class UsuarioUpdate(UsuarioCreate):
    pass


class UsuarioResponse(UsuarioBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    mensaje: str
