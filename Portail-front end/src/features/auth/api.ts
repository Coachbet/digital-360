import { api } from "@/shared/api/client";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "owner" | "admin" | "member";
  is_active: boolean;
  phone: string | null;
  telegram_linked: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  brand_primary: string;
  brand_ink: string;
  brand_accent: string;
  tagline: string | null;
  logo_storage_key: string | null;
  deck_template_key: string | null;
}

export interface Session {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization;
}

export const ROLE_LABELS: Record<User["role"], string> = {
  owner: "Propriétaire",
  admin: "Administrateur",
  member: "Membre",
};

export const authApi = {
  signup: (payload: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }) => api.post<Session>("/auth/signup", payload),

  login: (payload: { email: string; password: string }) =>
    api.post<Session>("/auth/login", payload),

  me: () => api.get<{ user: User; organization: Organization }>("/auth/me"),

  members: () => api.get<User[]>("/auth/members"),

  /** Numéro qui autorise l'accès au bot Telegram. null pour le retirer. */
  updatePhone: (phone: string | null) => api.put<User>("/auth/me/phone", { phone }),

  unlinkTelegram: () => api.delete<User>("/auth/me/telegram"),
};
