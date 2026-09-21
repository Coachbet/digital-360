import { api } from "@/shared/api/client";

export interface DataFile {
  id: string;
  client_id: string;
  period: string;
  filename: string;
  storage_key: string;
  content_type: string | null;
  size_bytes: number | null;
  uploaded_at: string;
}

export interface Period {
  period: string;
  file_count: number;
}

export const dataApi = {
  listPeriods: (clientId: string) =>
    api.get<Period[]>(`/data/clients/${clientId}/periods`),

  listFiles: (clientId: string, period?: string) => {
    const params = new URLSearchParams({ client_id: clientId });
    if (period) params.set("period", period);
    return api.get<DataFile[]>(`/data/files?${params}`);
  },

  upload: (clientId: string, period: string, files: FileList | File[]) => {
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append("files", file));
    const params = new URLSearchParams({ client_id: clientId, period });
    return api.postForm<DataFile[]>(`/data/files?${params}`, formData);
  },

  downloadUrl: (fileId: string) =>
    api.get<{ url: string; expires_in: number }>(`/data/files/${fileId}/download`),

  remove: (fileId: string) => api.delete<void>(`/data/files/${fileId}`),
};
