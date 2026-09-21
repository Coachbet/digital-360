/**
 * Point d'entrée unique de tous les appels à l'API.
 *
 * Centraliser ici permet d'attacher le jeton de session à chaque requête et de
 * réagir globalement à son expiration, sans que les modules métier aient à s'en
 * préoccuper.
 */

// En local, Vite relaie /api vers FastAPI. Pour un frontend hébergé séparément
// (par exemple sur Vercel), VITE_API_BASE_URL contient l'origine publique du
// backend, sans slash final : https://api.exemple.com.
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const BASE_URL = `${API_ORIGIN}/api/v1`;
const TOKEN_KEY = "d360.token";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

/** Prévenu quand une session expire, pour renvoyer l'utilisateur au login. */
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      // Navigation privée ou stockage bloqué : on fonctionne sans persistance.
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* session non persistée, sans conséquence fonctionnelle */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* rien à nettoyer */
    }
  },
};

function authHeaders(base: Record<string, string> = {}): Record<string, string> {
  const token = tokenStore.get();
  return token ? { ...base, Authorization: `Bearer ${token}` } : base;
}

async function handle<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    tokenStore.clear();
    onUnauthorized?.();
    throw new ApiError("Session expirée, reconnecte-toi", 401);
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      // FastAPI renvoie soit une chaîne, soit la liste d'erreurs de validation.
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
    } catch {
      /* réponse sans corps JSON */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  get<T>(path: string): Promise<T> {
    return fetch(`${BASE_URL}${path}`, { headers: authHeaders() }).then(handle<T>);
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(handle<T>);
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return fetch(`${BASE_URL}${path}`, {
      method: "PUT",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(handle<T>);
  },

  postForm<T>(path: string, formData: FormData): Promise<T> {
    // Pas de Content-Type explicite : le navigateur ajoute la frontière multipart.
    return fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    }).then(handle<T>);
  },

  delete<T>(path: string): Promise<T> {
    return fetch(`${BASE_URL}${path}`, {
      method: "DELETE",
      headers: authHeaders(),
    }).then(handle<T>);
  },
};
