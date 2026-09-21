// Appels HTTP vers le backend pour le module Calendrier.
// Exemple : GET /api/v1/calendar/events

export async function fetchEvents() {
  const res = await fetch("/api/v1/calendar/events");
  if (!res.ok) throw new Error("Impossible de récupérer les événements");
  return res.json();
}
