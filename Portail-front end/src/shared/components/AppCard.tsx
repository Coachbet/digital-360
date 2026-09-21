import { ArrowUpRight, LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/shared/components/ui/Badge";
import { cn } from "@/shared/lib/utils";

export interface AppCardProps {
  title: string;
  description: string;
  to: string;
  icon: LucideIcon;
  disabled?: boolean;
  badge?: string;
}

/**
 * Bloc « application » de la page d'accueil.
 *
 * Registre volontairement sobre : pastille d'icône discrète, pas d'aplat de
 * couleur par carte. Ce sont les livrables qui portent la couleur de l'agence,
 * l'interface reste neutre pour ne pas entrer en conflit avec elle.
 */
export default function AppCard({
  title,
  description,
  to,
  icon: Icon,
  disabled = false,
  badge,
}: AppCardProps) {
  const content = (
    <div
      className={cn(
        "group relative flex h-full min-h-[190px] flex-col justify-between overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-card transition-all",
        disabled
          ? "cursor-not-allowed opacity-60"
          : "hover:-translate-y-1 hover:border-primary/30 hover:shadow-card-hover",
      )}
    >
      <div className="flex items-start justify-between">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-soft text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
          <Icon className="h-5 w-5" />
        </span>
        <span className="flex items-center gap-2">
          {badge && <Badge tone="primary">{badge}</Badge>}
          {!disabled && (
            <ArrowUpRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
          )}
        </span>
      </div>

      <div>
        <h3 className="font-semibold tracking-tight">{title}</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </div>
  );

  if (disabled) return content;
  return (
    <Link to={to} className="block h-full">
      {content}
    </Link>
  );
}
