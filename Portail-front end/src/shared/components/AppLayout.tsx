import {
  Building2,
  CalendarDays,
  FolderOpen,
  LayoutGrid,
  LogOut,
  Megaphone,
  Receipt,
  Sparkles,
} from "lucide-react";
import { ReactNode, useState } from "react";
import { Link, NavLink } from "react-router-dom";

import { ROLE_LABELS } from "@/features/auth/api";
import { useAuth } from "@/features/auth/AuthContext";
import Logo from "@/shared/components/Logo";
import { cn } from "@/shared/lib/utils";

const NAV = [
  { to: "/", label: "Vue d'ensemble", icon: LayoutGrid, end: true },
  { to: "/data", label: "Données", icon: FolderOpen },
  { to: "/auto-review", label: "Rapports", icon: Sparkles },
  { to: "/publicite", label: "Publicité", icon: Megaphone },
  { to: "/calendrier", label: "Calendrier", icon: CalendarDays },
  { to: "/facturation", label: "Facturation", icon: Receipt },
  { to: "/agence", label: "Mon agence", icon: Building2 },
];

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, organization, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card md:flex">
        <Link to="/" className="px-6 py-6">
          <Logo />
        </Link>

        {organization && (
          <div className="mx-3 mb-4 rounded-xl bg-muted/70 px-3 py-2.5">
            <p className="truncate text-sm font-semibold">{organization.name}</p>
            <p className="text-xs text-muted-foreground">Espace agence</p>
          </div>
        )}

        <nav className="flex flex-1 flex-col gap-0.5 px-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-soft text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {user && (
          <div className="relative border-t border-border p-3">
            <button
              onClick={() => setMenuOpen((open) => !open)}
              className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors hover:bg-muted"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                {initials(user.full_name)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{user.full_name}</span>
                <span className="block text-xs text-muted-foreground">
                  {ROLE_LABELS[user.role]}
                </span>
              </span>
            </button>

            {menuOpen && (
              <div className="absolute bottom-16 left-3 right-3 overflow-hidden rounded-xl border border-border bg-card shadow-pop">
                <button
                  onClick={logout}
                  className="flex w-full items-center gap-2.5 px-4 py-3 text-sm text-danger transition-colors hover:bg-muted"
                >
                  <LogOut className="h-4 w-4" />
                  Se déconnecter
                </button>
              </div>
            )}
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto max-w-6xl px-6 py-10 md:px-10">{children}</div>
      </main>
    </div>
  );
}

/** En-tête de page réutilisable. */
export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}
