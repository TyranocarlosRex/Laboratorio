import type {
  AuthResponse,
  BootstrapPayload,
  LoginPayload,
  Movimiento,
  MovimientoPayload,
  Sustancia,
  SustanciaPayload,
  Usuario,
  UsuarioPayload,
} from "./types";

export const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "https://laboratorio-fn54.onrender.com";

type ApiOptions = {
  token?: string;
  method?: string;
  body?: unknown;
};

type SustanciaFilters = {
  nombre?: string;
  categoria?: string;
  nivel_riesgo?: string;
  estado?: string;
};

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

async function request<T>(
  baseUrl: string,
  path: string,
  { token, method = "GET", body }: ApiOptions = {},
): Promise<T> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data?.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg).join(". "));
    }
    throw new Error(detail || `Error HTTP ${response.status}`);
  }

  return data as T;
}

export function bootstrapAdmin(baseUrl: string, payload: BootstrapPayload) {
  return request<Usuario>(baseUrl, "/auth/bootstrap", {
    method: "POST",
    body: payload,
  });
}

export function login(baseUrl: string, payload: LoginPayload) {
  return request<AuthResponse>(baseUrl, "/auth/login", {
    method: "POST",
    body: payload,
  });
}

export function getSustancias(
  baseUrl: string,
  token: string,
  filters: SustanciaFilters,
) {
  const searchParams = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });
  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return request<Sustancia[]>(baseUrl, `/sustancias${suffix}`, { token });
}

export function createSustancia(
  baseUrl: string,
  token: string,
  payload: SustanciaPayload,
) {
  return request<Sustancia>(baseUrl, "/sustancias", {
    token,
    method: "POST",
    body: payload,
  });
}

export function deleteSustancia(baseUrl: string, token: string, id: number) {
  return request<{ mensaje: string }>(baseUrl, `/sustancias/${id}`, {
    token,
    method: "DELETE",
  });
}

export function getMovimientos(baseUrl: string, token: string) {
  return request<Movimiento[]>(baseUrl, "/movimientos", { token });
}

export function createMovimiento(
  baseUrl: string,
  token: string,
  payload: MovimientoPayload,
) {
  return request<{ mensaje: string; movimiento: Movimiento; sustancia: Sustancia }>(
    baseUrl,
    "/movimientos",
    {
      token,
      method: "POST",
      body: payload,
    },
  );
}

export function getUsuarios(baseUrl: string, token: string) {
  return request<Usuario[]>(baseUrl, "/usuarios", { token });
}

export function createUsuario(
  baseUrl: string,
  token: string,
  payload: UsuarioPayload,
) {
  return request<Usuario>(baseUrl, "/usuarios", {
    token,
    method: "POST",
    body: payload,
  });
}
