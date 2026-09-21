import { AlertTriangle, Check, ImageUp, Presentation, Save, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/features/auth/AuthContext";
import { OrganizationProfile, organizationApi } from "@/features/organization/api";
import { PageHeader } from "@/shared/components/AppLayout";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Input, Label, Textarea } from "@/shared/components/ui/Field";

const LEGAL_FIELDS: { key: keyof OrganizationProfile; label: string; long?: boolean }[] = [
  { key: "legal_name", label: "Raison sociale" },
  { key: "email", label: "Courriel" },
  { key: "phone", label: "Téléphone" },
  { key: "website", label: "Site web" },
  { key: "address", label: "Adresse", long: true },
  { key: "tax_number_1_label", label: "Libellé taxe 1" },
  { key: "tax_number_1", label: "Numéro taxe 1" },
  { key: "tax_number_2_label", label: "Libellé taxe 2" },
  { key: "tax_number_2", label: "Numéro taxe 2" },
  { key: "registration_number", label: "Numéro d'entreprise" },
  { key: "payment_terms", label: "Conditions de paiement", long: true },
  { key: "payment_details", label: "Coordonnées de paiement", long: true },
];

const COLORS: { key: keyof OrganizationProfile; label: string; hint: string }[] = [
  { key: "brand_primary", label: "Couleur d'accent", hint: "Titres, chiffres clés, pastilles" },
  { key: "brand_ink", label: "Couleur foncée", hint: "Couvertures et bandeaux" },
  { key: "brand_accent", label: "Couleur claire", hint: "Fonds de cartes et zones douces" },
];

export default function OrganizationPage() {
  const { setOrganization } = useAuth();
  const [profile, setProfile] = useState<OrganizationProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const logoInput = useRef<HTMLInputElement>(null);
  const templateInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    organizationApi
      .profile()
      .then(setProfile)
      .catch((e) => setError(e.message));
  }, []);

  if (!profile) return <div role={error ? "alert" : "status"} className="p-6">{error || "Chargement de l’agence…"}<Button variant="secondary" onClick={() => { setError(null); organizationApi.profile().then(setProfile).catch(e => setError(e.message)); }}>Réessayer</Button></div>;

  const missingLegal = LEGAL_FIELDS.filter(
    ({ key }) => !String(profile[key] ?? "").trim(),
  ).length;

  const patch = (updated: OrganizationProfile) => {
    setProfile(updated);
    // La barre latérale affiche le nom de l'agence : on la tient à jour.
    setOrganization({
      id: updated.id,
      name: updated.name,
      slug: updated.slug,
      brand_primary: updated.brand_primary,
      brand_ink: updated.brand_ink,
      brand_accent: updated.brand_accent,
      tagline: updated.tagline,
      logo_storage_key: updated.logo_storage_key,
      deck_template_key: updated.deck_template_key,
    });
  };

  const run = async (action: () => Promise<OrganizationProfile>, flash = false) => {
    setBusy(true);
    setError(null);
    try {
      patch(await action());
      if (flash) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2500);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Mon agence"
        description="Ces informations habillent vos livrables : les rapports et les factures sortent à votre nom et à vos couleurs, jamais à celles de Digital 360."
      />

      {error && (
        <div className="mb-6 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* ------------------------------------------------------- identité */}
        <Card>
          <CardContent className="space-y-5 p-6">
            <h2 className="font-semibold">Identité</h2>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="name">Nom affiché</Label>
                <Input
                  id="name"
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="tagline">Signature</Label>
                <Input
                  id="tagline"
                  value={profile.tagline ?? ""}
                  onChange={(e) => setProfile({ ...profile, tagline: e.target.value })}
                  placeholder="Grandissons ensemble !"
                />
              </div>
            </div>

            <div>
              <Label>Couleurs de marque</Label>
              <div className="grid gap-4 sm:grid-cols-3">
                {COLORS.map(({ key, label, hint }) => (
                  <div
                    key={key}
                    className="flex items-center gap-3 rounded-xl border border-border p-3"
                  >
                    <input
                      type="color"
                      aria-label={label}
                      value={String(profile[key] ?? "#000000")}
                      onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
                      className="h-10 w-10 cursor-pointer rounded-lg border border-border bg-transparent p-0.5"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{label}</span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {hint}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <input
                ref={logoInput}
                type="file"
                accept="image/png,image/jpeg"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) run(() => organizationApi.uploadLogo(file));
                }}
              />
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => logoInput.current?.click()}
              >
                <ImageUp className="h-4 w-4" />
                {profile.logo_storage_key ? "Remplacer le logo" : "Téléverser le logo"}
              </Button>
              {profile.logo_storage_key && (
                <Badge tone="success">
                  <Check className="mr-1 h-3 w-3" />
                  Logo en place
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* --------------------------------------------- gabarit PowerPoint */}
        <Card>
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-2">
              <Presentation className="h-4 w-4 text-primary" />
              <h2 className="font-semibold">Gabarit de présentation</h2>
            </div>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Déposez votre modèle PowerPoint : les rapports générés repartiront de ce
              fichier, en conservant vos masques, vos polices et votre mise en page. Sans
              gabarit, le portail utilise sa mise en page intégrée avec vos couleurs.
            </p>

            <input
              ref={templateInput}
              type="file"
              accept=".pptx,.potx"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) run(() => organizationApi.uploadDeckTemplate(file));
              }}
            />

            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => templateInput.current?.click()}
              >
                <Presentation className="h-4 w-4" />
                {profile.deck_template_key ? "Remplacer le gabarit" : "Déposer un gabarit"}
              </Button>

              {profile.deck_template_key ? (
                <>
                  <Badge tone="success">
                    <Check className="mr-1 h-3 w-3" />
                    Gabarit actif
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busy}
                    onClick={() => run(() => organizationApi.removeDeckTemplate())}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Retirer
                  </Button>
                </>
              ) : (
                <span className="text-xs text-muted-foreground">
                  Formats acceptés : .pptx et .potx
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* ------------------------------------------------ mentions légales */}
        <Card>
          <CardContent className="space-y-5 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-semibold">Coordonnées et mentions légales</h2>
              {missingLegal > 0 && (
                <Badge tone="warning">
                  <AlertTriangle className="mr-1 h-3 w-3" />
                  {missingLegal} champ{missingLegal > 1 ? "s" : ""} à compléter
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Ces mentions apparaissent en pied de vos factures. Les champs vides y sont
              imprimés « À compléter » — de quoi repérer une facture incomplète avant de
              l'envoyer.
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              {LEGAL_FIELDS.map(({ key, label, long }) => (
                <div key={key} className={long ? "sm:col-span-2" : undefined}>
                  <Label htmlFor={`org-${key}`}>{label}</Label>
                  {long ? (
                    <Textarea
                      id={`org-${key}`}
                      rows={2}
                      className="min-h-[40px]"
                      value={String(profile[key] ?? "")}
                      onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
                    />
                  ) : (
                    <Input
                      id={`org-${key}`}
                      value={String(profile[key] ?? "")}
                      onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
                    />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center gap-3">
          <Button
            size="lg"
            disabled={busy}
            onClick={() =>
              run(
                () =>
                  organizationApi.update({
                    name: profile.name,
                    tagline: profile.tagline,
                    brand_primary: profile.brand_primary,
                    brand_ink: profile.brand_ink,
                    brand_accent: profile.brand_accent,
                    ...Object.fromEntries(
                      LEGAL_FIELDS.map(({ key }) => [key, profile[key]]),
                    ),
                  }),
                true,
              )
            }
          >
            <Save className="h-4 w-4" />
            {saved ? "Enregistré" : "Enregistrer"}
          </Button>
          {saved && <span className="text-sm text-success">Modifications appliquées.</span>}
        </div>
      </div>
    </div>
  );
}
