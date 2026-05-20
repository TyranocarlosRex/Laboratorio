# Laboratorio API REST

Microservicio en Python con FastAPI para gestionar inventario de sustancias de laboratorio y registrar movimientos de entrada o salida.

## Base de datos

La API usa PostgreSQL mediante la variable obligatoria `DATABASE_URL`.
El proyecto usa un solo archivo `.env` local para configurar esa conexion.

1. Crea un proyecto en Supabase.
2. Entra a `Project Settings > Database > Connection string`.
3. Copia la cadena de conexion tipo PostgreSQL.
4. Configura `.env` en la raiz del proyecto.
5. Asegurate de que la URL termine con `sslmode=require`.

Ejemplo:

```env
DATABASE_URL=postgresql://USUARIO:CONTRASENA@HOST:5432/postgres?sslmode=require
JWT_SECRET_KEY=CAMBIA_ESTA_CLAVE_POR_UNA_CADENA_LARGA
JWT_EXPIRES_MINUTES=60
ALLOWED_ORIGINS=*
```

Si `DATABASE_URL` no existe, la API no inicia. Si `JWT_SECRET_KEY` no existe,
los endpoints protegidos no pueden emitir ni validar tokens.

Variables:

| Variable | Requerida | Descripcion |
| --- | --- | --- |
| `DATABASE_URL` | Si | Conexion PostgreSQL, en Supabase debe incluir `sslmode=require` |
| `JWT_SECRET_KEY` | Si | Clave privada para firmar tokens JWT |
| `JWT_EXPIRES_MINUTES` | No | Minutos de vida del token, por defecto `60` |
| `ALLOWED_ORIGINS` | No | Origenes CORS separados por coma, por defecto `*` |
| `PORT` | No | Puerto usado por Docker o por el proveedor de deploy, por defecto `8000` |

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

## Deploy

La aplicacion queda lista para proveedores que ejecutan un comando web con `PORT`.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
```

Si el proveedor usa Docker, el `Dockerfile` ya respeta `PORT`.

Checklist antes de publicar:

- Configura `DATABASE_URL`.
- Configura `JWT_SECRET_KEY` con una cadena larga y privada.
- Configura `JWT_EXPIRES_MINUTES=60` o el tiempo que quieras usar.
- Configura `ALLOWED_ORIGINS` con el dominio del frontend cuando ya exista.
- Usa `/health` como health check simple.
- Usa `/ready` para validar conexion a PostgreSQL y configuracion JWT.

Despues del primer deploy:

1. Abre `/ready` y confirma que responda `status: ready`.
2. Crea el primer administrador con `POST /auth/bootstrap`.
3. Inicia sesion con `POST /auth/login`.
4. Usa el token para consumir los endpoints protegidos.

## Recursos principales

Los endpoints de inventario y usuarios requieren token JWT en el header:

```text
Authorization: Bearer TU_TOKEN
```

| Metodo | Endpoint | Descripcion |
| --- | --- | --- |
| GET | `/health` | Verifica que el servicio esta activo |
| GET | `/ready` | Verifica que la API puede conectarse a PostgreSQL |
| POST | `/auth/bootstrap` | Crea el primer administrador si no hay usuarios |
| POST | `/auth/login` | Autentica usuario y devuelve token JWT |
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

## Autenticacion y roles

1. Con la tabla de usuarios vacia, crea el primer administrador:

```json
{
  "nombre": "Administrador",
  "contrasena": "clave-segura-123"
}
```

2. Inicia sesion en `/auth/login`:

```json
{
  "nombre": "Administrador",
  "contrasena": "clave-segura-123"
}
```

La respuesta incluye `access_token`, `token_type`, `expires_in` y el usuario autenticado.

Permisos por rol:

- `consultor`: puede consultar sustancias y movimientos.
- `responsable`: puede consultar y modificar sustancias y movimientos.
- `administrador`: puede hacer todo, incluyendo administrar usuarios.

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
- Si se registra, corrige o elimina un movimiento, el inventario se ajusta de forma transaccional.
- Los cambios de inventario bloquean la fila de la sustancia mientras termina la transaccion para evitar carreras entre solicitudes simultaneas.

## Filtros utiles

```text
GET /sustancias?nombre=acido
GET /sustancias?categoria=acido
GET /sustancias?nivel_riesgo=Alto
GET /sustancias?estado=bajo
GET /movimientos?id_sustancia=1
GET /movimientos?tipo=salida
```
