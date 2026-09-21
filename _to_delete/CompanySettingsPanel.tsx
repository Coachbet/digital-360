import { Building2, ImageUp, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { CompanySettings, invoicingApi } from "@/features/invoicing/api";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Input, Label, Textarea } from "@/shared/components/ui/Field";

const FIELDS: { key: keyof CompanySettings; label: string; multiline?: boolean }[] = [
  { key: "legal_name", label: "Raison sociale" },
  { key: "tagline", label: "Signature" },
  { key: "address", label: "Adresse", multiline: true },
  { key: "phone", label: "Téléphone" },
  { key: "email", label: "Courriel" },
  { key: "website", label: "Site web" },
  { key: "tax_number_1_label", label: "Libellé taxe 1" },
  { key: "tax_number_1", label: "Numéro taxe 1" },
  { key: "tax_number_2_label", label: "Libellé taxe 2" },
  { key: "tax_number_2", label: "Numéro taxe 2" },
  { key: "registration_number", label: "Numéro d'entreprise" },
  { key: "payment_terms", label: "Conditions de paiement", multiline: true },
  { key: "payment_details", label: "Coordonnées de paiement", multiline: true },
];

/**
 * Coordonnées imprimées sur les factures. Les mentions légales sont
 * initialisées à « À compléter » — rien n'est inventé, et il faut les
 * renseigner avant d'envoyer une vraie facture.
 */
export default function CompanySettingsPanel({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const logoInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    invoicingApi.settings().then(setSettings).catch((e) => onError(e.message));
  }, []);

  if (!settings) return null;

  const incomplete = FIELDS.filter(
    (f) => String(settings[f.key] ?? "").trim() === "À compléter",
  ).length;

  const save = async () => {
    setBusy(true);
    try {
      const updated = await invoicingApi.updateSettings(settings);
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const uploadLogo = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    try {
      setSettings(await invoicingApi.uploadLogo(file));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardContent className="space-y-5 p-6">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-primary" />
          <h2 className="font-semibold">Coordonnées de l'agence</h2>
        </div>

        {incomplete > 0 && (
          <p className="rounded-xl bg-warning/10 px-4 py-3 text-sm text-warning">
            {incomplete} champ{incomplete > 1 ? "s" : ""} encore à « À compléter ». Les
            factures québécoises doivent porter tes numéros de TPS et TVQ.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {FIELDS.map(({ key, label, multiline }) => (
            <div key={key} className={multiline ? "sm:col-span-2" : undefined}>
              <Label htmlFor={`cs-${key}`}>{label}</Label>
              {multiline ? (
                <Textarea
                  id={`cs-${key}`}
                  className="min-h-[40px]"
                  rows={2}
                  value={String(settings[key] ?? "")}
                  onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
                />
              ) : (
                <Input
                  id={`cs-${key}`}
                  value={String(settings[key] ?? "")}
                  onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
                />
              )}
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button disabled={busy} onClick={save}>
            <Save className="h-4 w-4" />
            {saved ? "Enregistré" : "Enregistrer"}
          </Button>

          <input
            ref={logoInput}
            type="file"
            accept="image/png,image/jpeg"
            className="hidden"
            onChange={(e) => uploadLogo(e.target.files?.[0])}
          />
          <Button variant="secondary" disabled={busy} onClick={() => logoInput.current?.click()}>
            <ImageUp className="h-4 w-4" />
            {settings.logo_storage_key ? "Remplacer le logo" : "Téléverser le logo"}
          </Button>

          <span className="text-xs text-muted-foreground">
            {settings.logo_storage_key
              ? "Logo utilisé en haut des factures."
              : "Sans logo, les factures affichent le monogramme ADIGI360."}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
