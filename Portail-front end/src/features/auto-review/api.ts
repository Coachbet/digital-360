import { api } from "@/shared/api/client";

export interface ClientType {
  value: string;
  label: string;
}

export interface Review {
  id: string;
  client_id: string;
  client_name: string;
  client_type: string;
  data_file_ids: string[];
  additional_info: string | null;
  status: string;
  status_label: string;
  error_message: string | null;
  report_filename: string | null;
  report_storage_key: string | null;
  created_at: string;
  approved_at: string | null;
}

export const autoReviewApi = {
  clientTypes: () => api.get<ClientType[]>("/auto-review/client-types"),

  list: (status?: string) =>
    api.get<Review[]>(`/auto-review${status ? `?status=${status}` : ""}`),

  launch: (payload: {
    client_id: string;
    data_file_ids: string[];
    selected_platforms: string[];
    additional_info?: string | null;
  }) => api.post<Review>("/auto-review", payload),

  /** Validation humaine : le rapport devient téléchargeable, rien n'est envoyé. */
  approve: (id: string) => api.post<Review>(`/auto-review/${id}/approve`),

  reportUrl: (id: string) =>
    api.get<{ url: string; filename: string; expires_in: number }>(
      `/auto-review/${id}/report`,
    ),

  previewUrl: (id: string) =>
    api.get<{ url: string; filename: string; expires_in: number; mode: string }>(
      `/auto-review/${id}/preview`,
    ),

  remove: (id: string) => api.delete<void>(`/auto-review/${id}`),
};
