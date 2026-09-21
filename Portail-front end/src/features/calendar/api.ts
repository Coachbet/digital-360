import { api } from "@/shared/api/client";

export interface CalendarEvent {
  id: string;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  category: string;
  client_id: string | null;
  source: "internal" | "google";
}

export interface Category {
  value: string;
  label: string;
}

export const calendarApi = {
  categories: () => api.get<Category[]>("/calendar/categories"),

  listEvents: (start?: Date, end?: Date) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start.toISOString());
    if (end) params.set("end", end.toISOString());
    const query = params.toString();
    return api.get<CalendarEvent[]>(`/calendar/events${query ? `?${query}` : ""}`);
  },

  create: (payload: {
    title: string;
    start_at: string;
    end_at: string;
    category: string;
    description?: string | null;
    client_id?: string | null;
  }) => api.post<CalendarEvent>("/calendar/events", payload),

  remove: (id: string) => api.delete<void>(`/calendar/events/${id}`),
};
