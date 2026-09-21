import { ArrowRight, BarChart3, FileText, Sparkles } from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { Button } from "@/shared/components/ui/Button";
import { Input, Label } from "@/shared/components/ui/Field";
import Logo from "@/shared/components/Logo";

type Mode = "login" | "signup";

const PITCH = [
  {
    icon: Sparkles,
    title: "Rapports rédigés par l'IA",
    text: "Vos exports deviennent une présentation commentée, à votre charte.",
  },
  {
    icon: BarChart3,
    title: "Toutes vos données au même endroit",
    text: "Meta, Google Ads, Shopify, Analytics — consolidés par client et par période.",
  },
  {
    icon: FileText,
    title: "Facturation intégrée",
    text: "Devis, factures et taxes générés depuis les mêmes fiches clients.",
  },
];

export default function AuthPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup({
          organization_name: organizationName,
          full_name: fullName,
          email,
          password,
        });
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_minmax(0,520px)]">
      {/* Colonne de présentation, masquée sur petit écran pour aller droit au formulaire */}
      <aside className="relative hidden overflow-hidden bg-ink p-14 text-ink-foreground lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-primary/30 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-40 -left-24 h-[24rem] w-[24rem] rounded-full bg-primary/20 blur-3xl"
        />

        <Logo className="relative" tone="light" />

        <div className="relative max-w-md">
          <h1 className="text-4xl font-bold leading-tight tracking-tight">
            Le reporting client,
            <br />
            sans les soirées à faire des slides.
          </h1>
          <p className="mt-4 text-white/70">
            Digital 360 rassemble vos données, rédige l'analyse et produit la
            présentation. Vous relisez, vous validez, vous envoyez.
          </p>

          <ul className="mt-10 space-y-6">
            {PITCH.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10">
                  <Icon className="h-5 w-5" />
                </span>
                <span>
                  <span className="block font-semibold">{title}</span>
                  <span className="block text-sm text-white/60">{text}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/40">
          Vos données restent cloisonnées par agence.
        </p>
      </aside>

      <main className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="lg:hidden">
            <Logo />
          </div>

          <h2 className="mt-8 text-2xl font-bold tracking-tight lg:mt-0">
            {mode === "login" ? "Connexion" : "Créer votre agence"}
          </h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {mode === "login"
              ? "Accédez à l'espace de votre agence."
              : "Quelques secondes suffisent. Vous serez propriétaire du compte."}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            {mode === "signup" && (
              <>
                <div>
                  <Label htmlFor="organization">Nom de l'agence</Label>
                  <Input
                    id="organization"
                    required
                    minLength={2}
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder="Studio Mercure"
                  />
                </div>
                <div>
                  <Label htmlFor="fullName">Votre nom</Label>
                  <Input
                    id="fullName"
                    required
                    minLength={2}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Camille Dupont"
                  />
                </div>
              </>
            )}

            <div>
              <Label htmlFor="email">Courriel professionnel</Label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="camille@studiomercure.com"
              />
            </div>

            <div>
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={mode === "signup" ? 10 : undefined}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
              />
              {mode === "signup" && (
                <p className="mt-1.5 text-xs text-muted-foreground">
                  10 caractères minimum.
                </p>
              )}
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger"
              >
                {error}
              </p>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={busy}>
              {busy ? "…" : mode === "login" ? "Se connecter" : "Créer mon agence"}
              {!busy && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            {mode === "login" ? "Pas encore de compte ?" : "Vous avez déjà un compte ?"}{" "}
            <button
              type="button"
              className="font-medium text-primary hover:underline"
              onClick={() => {
                setMode(mode === "login" ? "signup" : "login");
                setError(null);
              }}
            >
              {mode === "login" ? "Créer une agence" : "Se connecter"}
            </button>
          </p>
        </div>
      </main>
    </div>
  );
}
