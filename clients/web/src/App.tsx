import {
  AlertTriangle,
  Boxes,
  FlaskConical,
  LogIn,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  Settings,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  DEFAULT_API_BASE_URL,
  bootstrapAdmin,
  createMovimiento,
  createSustancia,
  createUsuario,
  deleteSustancia,
  getMovimientos,
  getSustancias,
  getUsuarios,
  login,
} from "./api";
import type {
  AuthResponse,
  Movimiento,
  MovimientoPayload,
  Role,
  Sustancia,
  SustanciaPayload,
  Usuario,
  UsuarioPayload,
} from "./types";

type Tab = "sustancias" | "movimientos" | "usuarios";

type LoginForm = {
  nombre: string;
  contrasena: string;
};

type SustanciaForm = {
  nombre: string;
  categoria: string;
  cantidad: string;
  unidad: string;
  nivel_riesgo: "Bajo" | "Medio" | "Alto";
  ubicacion: string;
  responsable: string;
  cantidad_minima: string;
  cantidad_maxima: string;
};

type MovimientoForm = {
  id_sustancia: string;
  tipo: "entrada" | "salida";
  cantidad: string;
  motivo: string;
};

const SESSION_KEY = "laboratorio.session";
const API_URL_KEY = "laboratorio.apiBaseUrl";

const emptyLoginForm: LoginForm = {
  nombre: "",
  contrasena: "",
};

const emptySustanciaForm: SustanciaForm = {
  nombre: "",
  categoria: "",
  cantidad: "0",
  unidad: "piezas",
  nivel_riesgo: "Medio",
  ubicacion: "",
  responsable: "",
  cantidad_minima: "0",
  cantidad_maxima: "",
};

const emptyMovimientoForm: MovimientoForm = {
  id_sustancia: "",
  tipo: "salida",
  cantidad: "1",
  motivo: "",
};

const emptyUsuarioForm: UsuarioPayload = {
  nombre: "",
  contrasena: "",
  rol: "consultor",
};

function readStoredSession(): AuthResponse | null {
  const rawSession = localStorage.getItem(SESSION_KEY);
  if (!rawSession) {
    return null;
  }

  try {
    return JSON.parse(rawSession) as AuthResponse;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("es-MX", {
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function parsePositiveNumber(value: string, fieldName: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${fieldName} debe ser mayor que cero`);
  }
  return parsed;
}

function parseNonNegativeNumber(value: string, fieldName: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${fieldName} no puede ser negativo`);
  }
  return parsed;
}

function roleLabel(role: Role): string {
  const labels: Record<Role, string> = {
    administrador: "Administrador",
    responsable: "Responsable",
    consultor: "Consultor",
  };
  return labels[role];
}

function riskClass(risk: Sustancia["nivel_riesgo"]): string {
  return `risk risk-${risk.toLowerCase()}`;
}

function statusClass(status: Sustancia["estado_inventario"]): string {
  return `status status-${status}`;
}

export function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(
    localStorage.getItem(API_URL_KEY) || DEFAULT_API_BASE_URL,
  );
  const [pendingApiBaseUrl, setPendingApiBaseUrl] = useState(apiBaseUrl);
  const [session, setSession] = useState<AuthResponse | null>(() =>
    readStoredSession(),
  );
  const [loginForm, setLoginForm] = useState<LoginForm>(emptyLoginForm);
  const [bootstrapForm, setBootstrapForm] =
    useState<LoginForm>(emptyLoginForm);
  const [sustanciaForm, setSustanciaForm] =
    useState<SustanciaForm>(emptySustanciaForm);
  const [movimientoForm, setMovimientoForm] =
    useState<MovimientoForm>(emptyMovimientoForm);
  const [usuarioForm, setUsuarioForm] =
    useState<UsuarioPayload>(emptyUsuarioForm);
  const [sustancias, setSustancias] = useState<Sustancia[]>([]);
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("sustancias");
  const [filters, setFilters] = useState({
    nombre: "",
    categoria: "",
    nivel_riesgo: "",
    estado: "",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const currentUser = session?.usuario ?? null;
  const token = session?.access_token ?? "";
  const canWrite =
    currentUser?.rol === "administrador" || currentUser?.rol === "responsable";
  const isAdmin = currentUser?.rol === "administrador";

  const metrics = useMemo(() => {
    const bajos = sustancias.filter(
      (sustancia) => sustancia.estado_inventario === "bajo",
    ).length;
    const excedidos = sustancias.filter(
      (sustancia) => sustancia.estado_inventario === "excedido",
    ).length;
    const salidas = movimientos.filter(
      (movimiento) => movimiento.tipo === "salida",
    ).length;

    return {
      sustancias: sustancias.length,
      alertas: bajos + excedidos,
      movimientos: movimientos.length,
      salidas,
    };
  }, [movimientos, sustancias]);

  useEffect(() => {
    if (session) {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
  }, [session]);

  useEffect(() => {
    if (!session) {
      return;
    }
    void refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, filters]);

  function showError(errorValue: unknown) {
    setMessage("");
    setError(errorValue instanceof Error ? errorValue.message : String(errorValue));
  }

  function showMessage(value: string) {
    setError("");
    setMessage(value);
  }

  async function refreshData() {
    if (!session) {
      return;
    }
    setLoading(true);
    try {
      const [nextSustancias, nextMovimientos, nextUsuarios] = await Promise.all([
        getSustancias(apiBaseUrl, token, filters),
        getMovimientos(apiBaseUrl, token),
        isAdmin ? getUsuarios(apiBaseUrl, token) : Promise.resolve([]),
      ]);
      setSustancias(nextSustancias);
      setMovimientos(nextMovimientos);
      setUsuarios(nextUsuarios);
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      const nextSession = await login(apiBaseUrl, loginForm);
      setSession(nextSession);
      setLoginForm(emptyLoginForm);
      showMessage(`Sesion iniciada como ${nextSession.usuario.nombre}`);
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  async function submitBootstrap(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      await bootstrapAdmin(apiBaseUrl, bootstrapForm);
      const nextSession = await login(apiBaseUrl, bootstrapForm);
      setSession(nextSession);
      setBootstrapForm(emptyLoginForm);
      showMessage("Administrador inicial creado");
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  function saveApiBaseUrl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUrl = pendingApiBaseUrl.trim().replace(/\/+$/, "");
    setApiBaseUrl(normalizedUrl);
    localStorage.setItem(API_URL_KEY, normalizedUrl);
    showMessage("URL de API actualizada");
  }

  function logout() {
    setSession(null);
    setSustancias([]);
    setMovimientos([]);
    setUsuarios([]);
    setActiveTab("sustancias");
  }

  async function submitSustancia(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload: SustanciaPayload = {
        nombre: sustanciaForm.nombre,
        categoria: sustanciaForm.categoria,
        cantidad: parseNonNegativeNumber(sustanciaForm.cantidad, "Cantidad"),
        unidad: sustanciaForm.unidad,
        nivel_riesgo: sustanciaForm.nivel_riesgo,
        ubicacion: sustanciaForm.ubicacion,
        responsable: sustanciaForm.responsable,
        cantidad_minima: parseNonNegativeNumber(
          sustanciaForm.cantidad_minima,
          "Cantidad minima",
        ),
        cantidad_maxima: sustanciaForm.cantidad_maxima
          ? parseNonNegativeNumber(sustanciaForm.cantidad_maxima, "Cantidad maxima")
          : null,
      };

      setLoading(true);
      await createSustancia(apiBaseUrl, token, payload);
      setSustanciaForm(emptySustanciaForm);
      showMessage("Sustancia registrada");
      await refreshData();
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  async function removeSustancia(id: number) {
    setLoading(true);
    try {
      await deleteSustancia(apiBaseUrl, token, id);
      showMessage("Sustancia eliminada");
      await refreshData();
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  async function submitMovimiento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const payload: MovimientoPayload = {
        id_sustancia: parsePositiveNumber(
          movimientoForm.id_sustancia,
          "Sustancia",
        ),
        tipo: movimientoForm.tipo,
        cantidad: parsePositiveNumber(movimientoForm.cantidad, "Cantidad"),
        motivo: movimientoForm.motivo,
      };

      setLoading(true);
      await createMovimiento(apiBaseUrl, token, payload);
      setMovimientoForm(emptyMovimientoForm);
      showMessage("Movimiento registrado");
      await refreshData();
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  async function submitUsuario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      await createUsuario(apiBaseUrl, token, usuarioForm);
      setUsuarioForm(emptyUsuarioForm);
      showMessage("Usuario creado");
      await refreshData();
    } catch (errorValue) {
      showError(errorValue);
    } finally {
      setLoading(false);
    }
  }

  if (!session) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <div className="brand-row">
            <div className="brand-mark">
              <FlaskConical size={28} />
            </div>
            <div>
              <h1>Laboratorio</h1>
              <p>Inventario de sustancias y movimientos</p>
            </div>
          </div>

          <form className="settings-bar" onSubmit={saveApiBaseUrl}>
            <Settings size={18} />
            <input
              aria-label="URL de API"
              value={pendingApiBaseUrl}
              onChange={(event) => setPendingApiBaseUrl(event.target.value)}
            />
            <button type="submit" title="Guardar URL de API">
              <Save size={18} />
            </button>
          </form>

          {error && <p className="alert alert-error">{error}</p>}
          {message && <p className="alert alert-ok">{message}</p>}

          <div className="auth-grid">
            <form className="panel" onSubmit={submitLogin}>
              <h2>Acceso</h2>
              <label>
                Usuario
                <input
                  required
                  value={loginForm.nombre}
                  onChange={(event) =>
                    setLoginForm({ ...loginForm, nombre: event.target.value })
                  }
                />
              </label>
              <label>
                Contrasena
                <input
                  required
                  minLength={8}
                  type="password"
                  value={loginForm.contrasena}
                  onChange={(event) =>
                    setLoginForm({
                      ...loginForm,
                      contrasena: event.target.value,
                    })
                  }
                />
              </label>
              <button className="primary" disabled={loading} type="submit">
                <LogIn size={18} />
                Entrar
              </button>
            </form>

            <form className="panel" onSubmit={submitBootstrap}>
              <h2>Primer administrador</h2>
              <label>
                Nombre
                <input
                  required
                  value={bootstrapForm.nombre}
                  onChange={(event) =>
                    setBootstrapForm({
                      ...bootstrapForm,
                      nombre: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Contrasena
                <input
                  required
                  minLength={8}
                  type="password"
                  value={bootstrapForm.contrasena}
                  onChange={(event) =>
                    setBootstrapForm({
                      ...bootstrapForm,
                      contrasena: event.target.value,
                    })
                  }
                />
              </label>
              <button className="secondary" disabled={loading} type="submit">
                <ShieldCheck size={18} />
                Crear
              </button>
            </form>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-row compact">
          <div className="brand-mark">
            <FlaskConical size={24} />
          </div>
          <div>
            <h1>Laboratorio</h1>
            <p>{apiBaseUrl}</p>
          </div>
        </div>
        <div className="session-actions">
          <div className="user-chip">
            <ShieldCheck size={16} />
            <span>{currentUser?.nombre}</span>
            <strong>{currentUser ? roleLabel(currentUser.rol) : ""}</strong>
          </div>
          <button className="icon-button" onClick={() => void refreshData()} title="Actualizar">
            <RefreshCw size={18} />
          </button>
          <button className="icon-button" onClick={logout} title="Cerrar sesion">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {error && <p className="alert alert-error">{error}</p>}
      {message && <p className="alert alert-ok">{message}</p>}

      <section className="metrics-grid">
        <article className="metric-card">
          <Boxes size={20} />
          <span>Sustancias</span>
          <strong>{metrics.sustancias}</strong>
        </article>
        <article className="metric-card">
          <AlertTriangle size={20} />
          <span>Alertas</span>
          <strong>{metrics.alertas}</strong>
        </article>
        <article className="metric-card">
          <RefreshCw size={20} />
          <span>Movimientos</span>
          <strong>{metrics.movimientos}</strong>
        </article>
        <article className="metric-card">
          <LogOut size={20} />
          <span>Salidas</span>
          <strong>{metrics.salidas}</strong>
        </article>
      </section>

      <nav className="tabs">
        <button
          className={activeTab === "sustancias" ? "active" : ""}
          onClick={() => setActiveTab("sustancias")}
        >
          <FlaskConical size={18} />
          Sustancias
        </button>
        <button
          className={activeTab === "movimientos" ? "active" : ""}
          onClick={() => setActiveTab("movimientos")}
        >
          <RefreshCw size={18} />
          Movimientos
        </button>
        {isAdmin && (
          <button
            className={activeTab === "usuarios" ? "active" : ""}
            onClick={() => setActiveTab("usuarios")}
          >
            <Users size={18} />
            Usuarios
          </button>
        )}
      </nav>

      {activeTab === "sustancias" && (
        <section className="content-grid">
          <form className="panel" onSubmit={submitSustancia}>
            <h2>Registrar sustancia</h2>
            <div className="form-grid">
              <label>
                Nombre
                <input
                  disabled={!canWrite}
                  required
                  value={sustanciaForm.nombre}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      nombre: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Categoria
                <input
                  disabled={!canWrite}
                  required
                  value={sustanciaForm.categoria}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      categoria: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Cantidad
                <input
                  disabled={!canWrite}
                  required
                  min="0"
                  step="0.01"
                  type="number"
                  value={sustanciaForm.cantidad}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      cantidad: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Unidad
                <input
                  disabled={!canWrite}
                  required
                  value={sustanciaForm.unidad}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      unidad: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Riesgo
                <select
                  disabled={!canWrite}
                  value={sustanciaForm.nivel_riesgo}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      nivel_riesgo: event.target
                        .value as SustanciaForm["nivel_riesgo"],
                    })
                  }
                >
                  <option>Bajo</option>
                  <option>Medio</option>
                  <option>Alto</option>
                </select>
              </label>
              <label>
                Ubicacion
                <input
                  disabled={!canWrite}
                  required
                  value={sustanciaForm.ubicacion}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      ubicacion: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Responsable
                <input
                  disabled={!canWrite}
                  required
                  value={sustanciaForm.responsable}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      responsable: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Minima
                <input
                  disabled={!canWrite}
                  min="0"
                  step="0.01"
                  type="number"
                  value={sustanciaForm.cantidad_minima}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      cantidad_minima: event.target.value,
                    })
                  }
                />
              </label>
              <label>
                Maxima
                <input
                  disabled={!canWrite}
                  min="0"
                  step="0.01"
                  type="number"
                  value={sustanciaForm.cantidad_maxima}
                  onChange={(event) =>
                    setSustanciaForm({
                      ...sustanciaForm,
                      cantidad_maxima: event.target.value,
                    })
                  }
                />
              </label>
            </div>
            <button className="primary" disabled={!canWrite || loading} type="submit">
              <Plus size={18} />
              Registrar
            </button>
          </form>

          <section className="panel list-panel">
            <div className="panel-header">
              <h2>Inventario</h2>
              <div className="filters">
                <input
                  aria-label="Filtrar por nombre"
                  placeholder="Nombre"
                  value={filters.nombre}
                  onChange={(event) =>
                    setFilters({ ...filters, nombre: event.target.value })
                  }
                />
                <input
                  aria-label="Filtrar por categoria"
                  placeholder="Categoria"
                  value={filters.categoria}
                  onChange={(event) =>
                    setFilters({ ...filters, categoria: event.target.value })
                  }
                />
                <select
                  aria-label="Filtrar por estado"
                  value={filters.estado}
                  onChange={(event) =>
                    setFilters({ ...filters, estado: event.target.value })
                  }
                >
                  <option value="">Estado</option>
                  <option value="normal">Normal</option>
                  <option value="bajo">Bajo</option>
                  <option value="excedido">Excedido</option>
                </select>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Cantidad</th>
                    <th>Riesgo</th>
                    <th>Estado</th>
                    <th>Ubicacion</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sustancias.map((sustancia) => (
                    <tr key={sustancia.id}>
                      <td>
                        <strong>{sustancia.nombre}</strong>
                        <span>{sustancia.categoria}</span>
                      </td>
                      <td>
                        {formatNumber(sustancia.cantidad)} {sustancia.unidad}
                      </td>
                      <td>
                        <span className={riskClass(sustancia.nivel_riesgo)}>
                          {sustancia.nivel_riesgo}
                        </span>
                      </td>
                      <td>
                        <span className={statusClass(sustancia.estado_inventario)}>
                          {sustancia.estado_inventario}
                        </span>
                      </td>
                      <td>{sustancia.ubicacion}</td>
                      <td>
                        {canWrite && (
                          <button
                            className="icon-button danger"
                            onClick={() => void removeSustancia(sustancia.id)}
                            title="Eliminar sustancia"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </section>
      )}

      {activeTab === "movimientos" && (
        <section className="content-grid">
          <form className="panel" onSubmit={submitMovimiento}>
            <h2>Registrar movimiento</h2>
            <label>
              Sustancia
              <select
                disabled={!canWrite}
                required
                value={movimientoForm.id_sustancia}
                onChange={(event) =>
                  setMovimientoForm({
                    ...movimientoForm,
                    id_sustancia: event.target.value,
                  })
                }
              >
                <option value="">Selecciona</option>
                {sustancias.map((sustancia) => (
                  <option key={sustancia.id} value={sustancia.id}>
                    {sustancia.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tipo
              <select
                disabled={!canWrite}
                value={movimientoForm.tipo}
                onChange={(event) =>
                  setMovimientoForm({
                    ...movimientoForm,
                    tipo: event.target.value as MovimientoForm["tipo"],
                  })
                }
              >
                <option value="entrada">Entrada</option>
                <option value="salida">Salida</option>
              </select>
            </label>
            <label>
              Cantidad
              <input
                disabled={!canWrite}
                min="0.01"
                required
                step="0.01"
                type="number"
                value={movimientoForm.cantidad}
                onChange={(event) =>
                  setMovimientoForm({
                    ...movimientoForm,
                    cantidad: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Motivo
              <textarea
                disabled={!canWrite}
                required
                value={movimientoForm.motivo}
                onChange={(event) =>
                  setMovimientoForm({
                    ...movimientoForm,
                    motivo: event.target.value,
                  })
                }
              />
            </label>
            <button className="primary" disabled={!canWrite || loading} type="submit">
              <Plus size={18} />
              Registrar
            </button>
          </form>

          <section className="panel list-panel">
            <div className="panel-header">
              <h2>Historial</h2>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Sustancia</th>
                    <th>Tipo</th>
                    <th>Cantidad</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {movimientos.map((movimiento) => {
                    const sustancia = sustancias.find(
                      (item) => item.id === movimiento.id_sustancia,
                    );
                    return (
                      <tr key={movimiento.id}>
                        <td>{formatDate(movimiento.fecha)}</td>
                        <td>{sustancia?.nombre ?? movimiento.id_sustancia}</td>
                        <td>
                          <span className={`movement movement-${movimiento.tipo}`}>
                            {movimiento.tipo}
                          </span>
                        </td>
                        <td>{formatNumber(movimiento.cantidad)}</td>
                        <td>{movimiento.motivo}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </section>
      )}

      {activeTab === "usuarios" && isAdmin && (
        <section className="content-grid">
          <form className="panel" onSubmit={submitUsuario}>
            <h2>Crear usuario</h2>
            <label>
              Nombre
              <input
                required
                value={usuarioForm.nombre}
                onChange={(event) =>
                  setUsuarioForm({ ...usuarioForm, nombre: event.target.value })
                }
              />
            </label>
            <label>
              Contrasena
              <input
                minLength={8}
                required
                type="password"
                value={usuarioForm.contrasena}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    contrasena: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Rol
              <select
                value={usuarioForm.rol}
                onChange={(event) =>
                  setUsuarioForm({
                    ...usuarioForm,
                    rol: event.target.value as Role,
                  })
                }
              >
                <option value="consultor">Consultor</option>
                <option value="responsable">Responsable</option>
                <option value="administrador">Administrador</option>
              </select>
            </label>
            <button className="primary" disabled={loading} type="submit">
              <Plus size={18} />
              Crear
            </button>
          </form>

          <section className="panel list-panel">
            <div className="panel-header">
              <h2>Usuarios</h2>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Rol</th>
                    <th>Creado</th>
                  </tr>
                </thead>
                <tbody>
                  {usuarios.map((usuario) => (
                    <tr key={usuario.id}>
                      <td>{usuario.nombre}</td>
                      <td>{roleLabel(usuario.rol)}</td>
                      <td>{formatDate(usuario.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </section>
      )}
    </main>
  );
}
