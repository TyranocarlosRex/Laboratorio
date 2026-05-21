export type Role = "administrador" | "responsable" | "consultor";

export type Usuario = {
  id: number;
  nombre: string;
  rol: Role;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  usuario: Usuario;
};

export type Sustancia = {
  id: number;
  nombre: string;
  categoria: string;
  cantidad: number;
  unidad: string;
  nivel_riesgo: "Bajo" | "Medio" | "Alto";
  ubicacion: string;
  responsable: string;
  cantidad_minima: number;
  cantidad_maxima: number | null;
  estado_inventario: "normal" | "bajo" | "excedido";
  created_at?: string | null;
  updated_at?: string | null;
};

export type SustanciaPayload = Omit<
  Sustancia,
  "id" | "estado_inventario" | "created_at" | "updated_at"
>;

export type Movimiento = {
  id: number;
  id_sustancia: number;
  tipo: "entrada" | "salida";
  cantidad: number;
  motivo: string;
  fecha?: string | null;
};

export type MovimientoPayload = Omit<Movimiento, "id" | "fecha">;

export type UsuarioPayload = {
  nombre: string;
  contrasena: string;
  rol: Role;
};

export type BootstrapPayload = {
  nombre: string;
  contrasena: string;
};

export type LoginPayload = BootstrapPayload;
