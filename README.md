# Laboratorio API REST

Microservicio en Python con FastAPI para gestionar inventario de sustancias de laboratorio y registrar movimientos de entrada o salida.

## Base de datos

La API usa PostgreSQL mediante la variable obligatoria `DATABASE_URL`.

1. Crea un proyecto en Supabase.
2. Entra a `Project Settings > Database > Connection string`.
3. Copia la cadena de conexion tipo PostgreSQL.
4. Configura `.env` usando `.env.example` como referencia.
5. Asegurate de que la URL termine con `sslmode=require`.

Ejemplo:

```env
DATABASE_URL=postgresql://postgres.qfayenewprwshefxebbf:TU_PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

Si `DATABASE_URL` no existe, la API no inicia.

## Ejecutar localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger queda disponible en:

```text
http://127.0.0.1:8000/docs
```

## Ejecutar con Docker

```bash
docker compose up --build
```

La API queda disponible en:

```text
http://127.0.0.1:8000
```

## Recursos principales

| Metodo | Endpoint | Descripcion |
| --- | --- | --- |
| GET | `/health` | Verifica que el servicio esta activo |
| GET | `/sustancias` | Lista sustancias con filtros opcionales |
| GET | `/sustancias/{id}` | Consulta una sustancia |
| POST | `/sustancias` | Registra una sustancia |
| PUT | `/sustancias/{id}` | Actualiza una sustancia |
| DELETE | `/sustancias/{id}` | Elimina una sustancia sin movimientos |
| GET | `/sustancias/alertas` | Lista sustancias con inventario bajo o excedido |
| GET | `/movimientos` | Lista movimientos |
| POST | `/movimientos` | Registra entrada o salida |
| PUT | `/movimientos/{id}` | Corrige un movimiento y ajusta inventario |
| DELETE | `/movimientos/{id}` | Elimina un movimiento y revierte inventario |
| GET | `/usuarios` | Lista usuarios sin exponer contrasenas |

## Ejemplo: registrar sustancia

```json
{
  "nombre": "Acido clorhidrico",
  "categoria": "Acido",
  "cantidad": 5,
  "unidad": "litros",
  "nivel_riesgo": "Alto",
  "ubicacion": "Estante A-2",
  "responsable": "Encargado de laboratorio",
  "cantidad_minima": 1,
  "cantidad_maxima": 20
}
```

## Ejemplo: registrar movimiento

```json
{
  "id_sustancia": 1,
  "tipo": "salida",
  "cantidad": 1,
  "motivo": "Uso en practica de quimica"
}
```

Al registrar un movimiento:

- `entrada` aumenta la existencia de la sustancia.
- `salida` disminuye la existencia.
- La API rechaza salidas mayores a la cantidad disponible.
- La API rechaza cantidades negativas o en cero para movimientos.
- Si se corrige o elimina un movimiento, el inventario se ajusta de forma transaccional.

## Filtros utiles

```text
GET /sustancias?nombre=acido
GET /sustancias?categoria=acido
GET /sustancias?nivel_riesgo=Alto
GET /sustancias?estado=bajo
GET /movimientos?id_sustancia=1
GET /movimientos?tipo=salida
```
