import { cn } from "@/shared/lib/utils";

/**
 * Marque du produit. Le sigle est dessiné en SVG plutôt qu'importé en image :
 * il suit la couleur du texte, reste net à toutes les tailles et n'ajoute
 * aucune requête réseau.
 */
export default function Logo({
  className,
  tone = "dark",
  compact = false,
}: {
  className?: string;
  tone?: "dark" | "light";
  compact?: boolean;
}) {
  const text = tone === "light" ? "text-white" : "text-foreground";

  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0" aria-hidden>
        <rect width="32" height="32" rx="9" fill="hsl(var(--primary))" />
        {/* Trois arcs : l'idée du « 360 », lisible même à 16 px */}
        <path
          d="M10 16a6 6 0 0 1 6-6"
          stroke="white"
          strokeWidth="2.6"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M22 16a6 6 0 0 1-6 6"
          stroke="white"
          strokeWidth="2.6"
          strokeLinecap="round"
          fill="none"
        />
        <circle cx="16" cy="16" r="2.4" fill="white" />
      </svg>

      {!compact && (
        <span className={cn("text-lg font-bold tracking-tight", text)}>
          Digital<span className="text-primary">360</span>
        </span>
      )}
    </span>
  );
}
