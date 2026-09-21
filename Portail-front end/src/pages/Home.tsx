import {
  ArrowUpRight,
  Building2,
  CalendarDays,
  FolderOpen,
  Megaphone,
  Receipt,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "@/features/auth/AuthContext";
import AppCard from "@/shared/components/AppCard";
import { PageHeader } from "@/shared/components/AppLayout";
import { api } from "@/shared/api/client";

interface Review {
  id: string;
  status: string;
}
interface Invoice {
  id: string;
  status: string;
  total: string;
  currency: string;
}
interface Client {
  id: string;
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Bonjour";
  if (hour < 18) return "Bon après-midi";
  return "Bonsoir";
}

export default function HomePage() {
  const { user, organization } = useAuth();
  const [toReview, setToReview] = useState(0);
  const [clients, setClients] = useState(0);
  const [unpaid, setUnpaid] = useState(0);

  useEffect(() => {
    // Chaque compteur est indépendant : un module en erreur n'empêche pas les
    // autres de s'afficher.
    api
      .get<Review[]>("/auto-review?status=awaiting_approval")
      .then((r) => setToReview(r.length))
      .catch(() => undefined);
    api
      .get<Client[]>("/clients")
      .then((r) => setClients(r.length))
      .catch(() => undefined);
    api
      .get<Invoice[]>("/invoices?status=issued")
      .then((r) => setUnpaid(r.length))
      .catch(() => undefined);
  }, []);

  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <div>
      <PageHeader
        title={`${greeting()}${firstName ? `, ${firstName}` : ""}`}
        description={
          organization
            ? `Espace de ${organization.name}. Voici où en sont vos clients aujourd'hui.`
            : undefined
        }
      />

      {/* Bandeau de synthèse : trois chiffres qui disent quoi faire maintenant */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        {[
          {
            value: toReview,
            label: toReview > 1 ? "rapports à relire" : "rapport à relire",
            to: "/auto-review",
            highlight: toReview > 0,
          },
          {
            value: unpaid,
            label: unpaid > 1 ? "factures en attente" : "facture en attente",
            to: "/facturation",
            highlight: false,
          },
          {
            value: clients,
            label: clients > 1 ? "clients actifs" : "client actif",
            to: "/data",
            highlight: false,
          },
        ].map(({ value, label, to, highlight }) => (
          <Link
            key={label}
            to={to}
            className={`group rounded-2xl border p-5 transition-all hover:-translate-y-0.5 hover:shadow-card ${
              highlight
                ? "border-primary/30 bg-primary-soft"
                : "border-border bg-card shadow-card"
            }`}
          >
            <div className="flex items-start justify-between">
              <span
                className={`text-3xl font-bold tracking-tight ${
                  highlight ? "text-primary" : "text-foreground"
                }`}
              >
                {value}
              </span>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{label}</p>
          </Link>
        ))}
      </div>

      <h2 className="mb-4 text-sm font-semibold text-muted-foreground">Applications</h2>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <AppCard
          title="Données"
          description="Déposez et organisez les fichiers sources de chaque client, par période."
          to="/data"
          icon={FolderOpen}
        />
        <AppCard
          title="Rapports"
          description="Lancez l'analyse, relisez la présentation produite, validez-la."
          to="/auto-review"
          icon={Sparkles}
          badge={toReview ? `${toReview} à relire` : undefined}
        />
        <AppCard
          title="Publicité"
          description="Suivez les KPI Meta Ads et publiez vos contenus Instagram."
          to="/publicite"
          icon={Megaphone}
        />
        <AppCard
          title="Calendrier"
          description="Échéances de rapports, campagnes, rendez-vous et planning d'équipe."
          to="/calendrier"
          icon={CalendarDays}
        />
        <AppCard
          title="Facturation"
          description="Saisissez les prestations, récupérez la facture en PDF à votre charte."
          to="/facturation"
          icon={Receipt}
        />
        <AppCard
          title="Mon agence"
          description="Couleurs, logo, gabarit de présentation et mentions légales."
          to="/agence"
          icon={Building2}
        />
      </div>
    </div>
  );
}
