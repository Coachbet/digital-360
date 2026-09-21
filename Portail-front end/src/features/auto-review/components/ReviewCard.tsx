import { AlertCircle, CheckCircle2, Download, Eye, FileText, Loader2, Trash2, X } from "lucide-react";
import { useState } from "react";

import { Review, autoReviewApi } from "@/features/auto-review/api";
import { Badge, BadgeTone } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";

const STATUS_TONE: Record<string, BadgeTone> = {
  pending: "neutral",
  processing: "warning",
  awaiting_approval: "primary",
  approved: "success",
  failed: "danger",
};

/**
 * Une review dans la liste. Le rapport se relit, se valide, puis se télécharge —
 * aucun envoi automatique n'intervient.
 */
export default function ReviewCard({
  review,
  onChanged,
  onError,
}: {
  review: Review;
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const approve = async () => {
    setBusy(true);
    try {
      await autoReviewApi.approve(review.id);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const download = async () => {
    try {
      const { url } = await autoReviewApi.reportUrl(review.id);
      window.open(url, "_blank");
    } catch (e) {
      onError((e as Error).message);
    }
  };

  const openPreview = async () => {
    setBusy(true);
    try {
      const { url } = await autoReviewApi.previewUrl(review.id);
      setPreview(url);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Supprimer définitivement ce rapport ?")) return;
    setBusy(true);
    try {
      await autoReviewApi.remove(review.id);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="font-medium">{review.client_name}</p>
              <Badge tone={STATUS_TONE[review.status] ?? "neutral"}>
                {review.status_label}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {review.data_file_ids.length} fichier
              {review.data_file_ids.length > 1 ? "s" : ""} ·{" "}
              {new Date(review.created_at).toLocaleString("fr-FR")}
            </p>
            {review.report_filename && (
              <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <FileText className="h-3 w-3" />
                {review.report_filename}
              </p>
            )}
            {review.approved_at && (
              <p className="mt-1 text-xs text-success">
                Validé le {new Date(review.approved_at).toLocaleString("fr-FR")}
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {review.status === "processing" && (
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Analyse en cours
              </span>
            )}

            {review.report_storage_key && (
              <Button variant="secondary" size="sm" disabled={busy} onClick={openPreview}>
                <Eye className="h-3.5 w-3.5" /> Aperçu
              </Button>
            )}

            {review.report_storage_key && (
              <Button variant="secondary" size="sm" onClick={download}>
                <Download className="h-3.5 w-3.5" />
                {review.status === "awaiting_approval" ? "Relire" : "Télécharger"}
              </Button>
            )}
            <Button variant="ghost" size="sm" disabled={busy} onClick={remove} title="Supprimer le rapport">
              <Trash2 className="h-3.5 w-3.5" /> Supprimer
            </Button>

            {review.status === "awaiting_approval" && (
              <Button size="sm" disabled={busy} onClick={approve}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                {busy ? "..." : "Valider"}
              </Button>
            )}
          </div>
        </div>

        {review.error_message && (
          <p className="flex items-start gap-1.5 rounded-lg bg-danger/5 px-3 py-2 text-xs text-danger">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {review.error_message}
          </p>
        )}
      </CardContent>
      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Aperçu du rapport PowerPoint">
          <div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-background shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div><p className="font-semibold">{review.report_filename}</p><p className="text-xs text-muted-foreground">Aperçu PDF fidèle au PowerPoint</p></div>
              <Button variant="ghost" size="icon" onClick={() => setPreview(null)} title="Fermer"><X className="h-4 w-4" /></Button>
            </div>
            <iframe src={preview} title={`Aperçu de ${review.report_filename}`} className="min-h-0 flex-1 bg-muted" />
          </div>
        </div>
      )}
    </Card>
  );
}
