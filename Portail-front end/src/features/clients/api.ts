import { api } from "@/shared/api/client";

export interface Client {
  id: string;
  name: string;
  client_type: string;
  contact_email: string | null;
  created_at: string;
}

export const clientsApi = {
  list: () => api.get<Client[]>("/clients"),
  create: (payload: { name: string; client_type: string; contact_email?: string | null }) =>
    api.post<Client>("/clients", payload),
  remove: (id: string) => api.delete<void>(`/clients/${id}`),
};
