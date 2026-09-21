import { api } from "@/shared/api/client";

export interface AdvertisingConnection {
  connected: boolean;
  client_id: string | null;
  meta_ad_account_id: string | null;
  instagram_user_id: string | null;
  has_meta_token: boolean;
  has_instagram_token: boolean;
}

export interface AdvertisingKpis {
  date_preset: string;
  currency: string | null;
  spend: number;
  impressions: number;
  reach: number;
  clicks: number;
  ctr: number;
  cpc: number;
  cpm: number;
  conversions: number;
  purchase_roas: number;
}

export interface CredentialField {
  key: string;
  label: string;
  required: boolean;
  secret: boolean;
  placeholder: string;
  help: string;
}

export interface AdvertisingPlatform {
  value: string;
  label: string;
  description: string;
  credential_fields: CredentialField[];
}

export interface PlatformConnection {
  platform: string;
  label: string;
  connected: boolean;
  client_id: string;
  account_id: string;
  configured_fields: string[];
}

export const advertisingApi = {
  platforms: () => api.get<AdvertisingPlatform[]>("/advertising/platforms"),

  connections: (clientId: string) =>
    api.get<PlatformConnection[]>(
      `/advertising/connections?client_id=${encodeURIComponent(clientId)}`,
    ),

  savePlatformConnection: (
    platform: string,
    payload: { client_id: string; account_id: string; credentials: Record<string, string> },
  ) => api.put<PlatformConnection>(`/advertising/connections/${platform}`, payload),

  removePlatformConnection: (platform: string, clientId: string) =>
    api.delete<void>(
      `/advertising/connections/${platform}?client_id=${encodeURIComponent(clientId)}`,
    ),

  platformKpis: (platform: string, clientId: string, datePreset: string) =>
    api.get<AdvertisingKpis>(
      `/advertising/connections/${platform}/kpis?client_id=${encodeURIComponent(clientId)}&date_preset=${encodeURIComponent(datePreset)}`,
    ),
  connection: (clientId: string) =>
    api.get<AdvertisingConnection>(
      `/advertising/connection?client_id=${encodeURIComponent(clientId)}`,
    ),

  saveConnection: (payload: {
    client_id: string;
    meta_ad_account_id: string;
    instagram_user_id: string;
    meta_access_token?: string;
    instagram_access_token?: string;
  }) => api.put<AdvertisingConnection>("/advertising/connection", payload),

  disconnect: (clientId: string) =>
    api.delete<void>(`/advertising/connection?client_id=${encodeURIComponent(clientId)}`),

  kpis: (clientId: string, datePreset: string) =>
    api.get<AdvertisingKpis>(
      `/advertising/kpis?client_id=${encodeURIComponent(clientId)}&date_preset=${encodeURIComponent(datePreset)}`,
    ),

  publishInstagram: (clientId: string, image: File, caption: string) => {
    const form = new FormData();
    form.append("client_id", clientId);
    form.append("image", image);
    form.append("caption", caption);
    return api.postForm<{ id: string; message: string }>("/advertising/instagram/posts", form);
  },
};
