import { api } from "@/shared/api/client";

export interface InvoiceLine {
  description: string;
  quantity: string;
  unit_price: string;
}

export interface Invoice {
  id: string;
  number: string;
  client_id: string | null;
  client_name: string;
  client_address: string | null;
  client_email: string | null;
  lines: InvoiceLine[];
  currency: string;
  tax_regime: string;
  discount: string;
  status: string;
  issue_date: string;
  due_date: string | null;
  notes: string | null;
  subtotal: string;
  tax_total: string;
  total: string;
  pdf_storage_key: string | null;
  created_at: string;
}

export interface Option {
  value: string;
  label: string;
}

export interface InvoiceOptions {
  currencies: Option[];
  tax_regimes: Option[];
  statuses: Option[];
}

export interface InvoiceCreatePayload {
  client_name: string;
  lines: { description: string; quantity: number; unit_price: number }[];
  issue_date: string;
  due_date?: string | null;
  client_id?: string | null;
  client_address?: string | null;
  client_email?: string | null;
  currency: string;
  tax_regime: string;
  discount?: number;
  notes?: string | null;
  signature_data_url?: string | null;
}

export const invoicingApi = {
  options: () => api.get<InvoiceOptions>("/invoices/options"),
  list: () => api.get<Invoice[]>("/invoices"),
  create: (payload: InvoiceCreatePayload) => api.post<Invoice>("/invoices", payload),
  pdfUrl: (id: string) =>
    api.get<{ url: string; filename: string; expires_in: number }>(`/invoices/${id}/pdf`),
  setStatus: (id: string, status: string) =>
    api.post<Invoice>(`/invoices/${id}/status?status=${status}`)
};
