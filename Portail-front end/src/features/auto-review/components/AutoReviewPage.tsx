import { Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Review, autoReviewApi } from "@/features/auto-review/api";
import ReviewCard from "@/features/auto-review/components/ReviewCard";
import ReviewForm from "@/features/auto-review/components/ReviewForm";
import { PageHeader } from "@/shared/components/AppLayout";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Label, Select } from "@/shared/components/ui/Field";
import { Button } from "@/shared/components/ui/Button";

/** Statuts qui évoluent sans action de l'utilisateur : n8n travaille encore. */
const IN_PROGRESS = new Set(["pending", "processing"]);

const POLL_MS = 5000;
/** Au-delà, on cesse d'interroger : n8n ne répondra probablement plus. */
const MAX_POLL_MS = 10 * 60 * 1000;

export default function AutoReviewPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const startedAt = useRef<number | null>(null);

  const refresh = useCallback(
    () =>
      autoReviewApi
        .list()
        .then(setReviews)
        .catch((e) => setError(e.message)),
    [],
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Sondage conditionnel : on n'interroge le serveur que tant qu'un rapport est
  // effectivement en cours de génération. Une page ouverte sur des rapports déjà
  // validés ne génère aucun trafic — l'ancien intervalle inconditionnel tournait
  // en continu et saturait les journaux du backend pour rien.
  const pending = reviews.some((review) => IN_PROGRESS.has(review.status));
  const reportClients = useMemo(
    () => Array.from(new Map(reviews.map((review) => [review.client_id, review.client_name]))),
    [reviews],
  );
  const visibleReviews = selectedClientId
    ? reviews.filter((review) => review.client_id === selectedClientId)
    : reviews;

  useEffect(() => {
    if (!pending) {
      startedAt.current = null;
      return;
    }
    if (startedAt.current === null) startedAt.current = Date.now();

    const timer = setInterval(() => {
      if (startedAt.current !== null && Date.now() - startedAt.current > MAX_POLL_MS) {
        setError("L’analyse prend plus de temps que prévu. Clique sur Actualiser les rapports et vérifie les exécutions n8n si elle reste bloquée.");
        startedAt.current = null;
        return;
      }
      // Onglet en arrière-plan : inutile de solliciter le serveur.
      if (document.visibilityState === "visible") refresh();
    }, POLL_MS);

    return () => clearInterval(timer);
  }, [pending, refresh]);

  return (
    <div>
      <PageHeader
        title="Auto Review"
        description="Lance l’analyse d’un rapport, relis le PowerPoint produit, puis valide-le. Rien n’est envoyé : le fichier se télécharge depuis le portail."
        action={
          <div>
            <Button variant="secondary" onClick={() => { setError(null); startedAt.current = Date.now(); void refresh(); }}>Actualiser les rapports</Button>
            <Label htmlFor="reports-client">Afficher les rapports de</Label>
            <Select
              id="reports-client"
              className="min-w-52"
              value={selectedClientId}
              onChange={(event) => setSelectedClientId(event.target.value)}
            >
              <option value="">Tous les clients</option>
              {reportClients.map(([id, name]) => (
                <option key={id} value={id}>{name}</option>
              ))}
            </Select>
          </div>
        }
      />

      {error && (
        <div className="mb-6 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        <ReviewForm onLaunched={refresh} onError={setError} />

        <div>
          <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
            Rapports ({visibleReviews.length})
          </h2>

          {visibleReviews.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-2 p-16 text-center">
                <Sparkles className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Aucun rapport pour ce client
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {visibleReviews.map((review) => (
                <ReviewCard
                  key={review.id}
                  review={review}
                  onChanged={refresh}
                  onError={setError}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
