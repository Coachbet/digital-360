// Appels HTTP vers le backend pour le module Auto Review.
// Exemple : POST /api/v1/auto-review avec les infos du formulaire.

import type { AutoReviewRequest } from "./../types";

export async function submitAutoReview(payload: AutoReviewRequest) {
  const res = await fetch("/api/v1/auto-review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Échec de l'envoi de la review automatique");
  return res.json();
}
