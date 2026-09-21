import { PenLine, Plus, Receipt, Trash2, Upload, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Client, clientsApi } from "@/features/clients/api";
import { InvoiceOptions, invoicingApi } from "@/features/invoicing/api";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Input, Label, Select, Textarea } from "@/shared/components/ui/Field";

interface DraftLine {
  description: string;
  quantity: string;
  unit_price: string;
}

const EMPTY_LINE: DraftLine = { description: "", quantity: "1", unit_price: "" };

/** Taux appliqués côté client uniquement pour l'aperçu ; le backend refait le
 *  calcul qui fait foi au moment de générer le PDF. */
const PREVIEW_RATES: Record<string, { label: string; rate: number }[]> = {
  qc_gst_qst: [
    { label: "TPS (5 %)", rate: 0.05 },
    { label: "TVQ (9,975 %)", rate: 0.09975 },
  ],
  gst_only: [{ label: "TPS (5 %)", rate: 0.05 }],
  eu_vat_20: [{ label: "TVA (20 %)", rate: 0.2 }],
  none: [],
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function inDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function InvoiceForm({
  onCreated,
  onError,
}: {
  onCreated: () => void;
  onError: (message: string) => void;
}) {
  const [options, setOptions] = useState<InvoiceOptions | null>(null);
  const [clients, setClients] = useState<Client[]>([]);

  const [clientId, setClientId] = useState("");
  const [clientName, setClientName] = useState("");
  const [clientAddress, setClientAddress] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [issueDate, setIssueDate] = useState(today);
  const [dueDate, setDueDate] = useState(() => inDays(30));
  const [currency, setCurrency] = useState("CAD");
  const [taxRegime, setTaxRegime] = useState("qc_gst_qst");
  const [discount, setDiscount] = useState("0");
  const [notes, setNotes] = useState("");
  const [signature, setSignature] = useState<string | null>(null);
  const [lines, setLines] = useState<DraftLine[]>([{ ...EMPTY_LINE }]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    invoicingApi.options().then(setOptions).catch((e) => onError(e.message));
    clientsApi.list().then(setClients).catch(() => undefined);
  }, []);

  const totals = useMemo(() => {
    const subtotalGross = lines.reduce(
      (sum, line) => sum + (Number(line.quantity) || 0) * (Number(line.unit_price) || 0),
      0,
    );
    const subtotal = Math.max(0, subtotalGross - (Number(discount) || 0));
    const taxes = (PREVIEW_RATES[taxRegime] ?? []).map((t) => ({
      label: t.label,
      amount: subtotal * t.rate,
    }));
    return {
      subtotal,
      taxes,
      total: subtotal + taxes.reduce((sum, t) => sum + t.amount, 0),
    };
  }, [lines, discount, taxRegime]);

  const money = (value: number) =>
    value.toLocaleString("fr-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) +
    (currency === "EUR" ? " €" : " $");

  const updateLine = (index: number, patch: Partial<DraftLine>) =>
    setLines((current) =>
      current.map((line, i) => (i === index ? { ...line, ...patch } : line)),
    );

  const canSubmit =
    clientName.trim() &&
    lines.some((l) => l.description.trim() && Number(l.quantity) > 0) &&
    !busy;

  const submit = async () => {
    setBusy(true);
    try {
      await invoicingApi.create({
        client_name: clientName.trim(),
        client_id: clientId || null,
        client_address: clientAddress || null,
        client_email: clientEmail || null,
        issue_date: issueDate,
        due_date: dueDate || null,
        currency,
        tax_regime: taxRegime,
        discount: Number(discount) || 0,
        notes: notes || null,
        signature_data_url: signature,
        lines: lines
          .filter((l) => l.description.trim())
          .map((l) => ({
            description: l.description.trim(),
            quantity: Number(l.quantity) || 0,
            unit_price: Number(l.unit_price) || 0,
          })),
      });
      setLines([{ ...EMPTY_LINE }]);
      setNotes("");
      setDiscount("0");
      setSignature(null);
      onCreated();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardContent className="space-y-6 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label htmlFor="inv-client">Client</Label>
            <Select
              id="inv-client"
              value={clientId}
              onChange={(e) => {
                const id = e.target.value;
                setClientId(id);
                const found = clients.find((c) => c.id === id);
                if (found) {
                  setClientName(found.name);
                  setClientEmail(found.contact_email ?? "");
                }
              }}
            >
              <option value="">— Saisie libre —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>

          <div className="sm:col-span-2">
            <Label htmlFor="inv-name">Raison sociale facturée</Label>
            <Input
              id="inv-name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="Boutique Lumière Inc."
            />
          </div>

          <div>
            <Label htmlFor="inv-email">Courriel</Label>
            <Input
              id="inv-email"
              type="email"
              value={clientEmail}
              onChange={(e) => setClientEmail(e.target.value)}
              placeholder="compta@client.ca"
            />
          </div>

          <div>
            <Label htmlFor="inv-address">Adresse</Label>
            <Textarea
              id="inv-address"
              className="min-h-[40px]"
              rows={2}
              value={clientAddress}
              onChange={(e) => setClientAddress(e.target.value)}
              placeholder={"4200 rue Saint-Denis\nMontréal, QC H2J 2K9"}
            />
          </div>
        </div>

        <div>
          <Label>Signature autorisée</Label>
          <div className="mt-1 flex min-h-28 items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 p-4">
            {signature ? (
              <div className="flex w-full items-center justify-between gap-4">
                <img src={signature} alt="Aperçu de la signature" className="max-h-20 max-w-[260px] object-contain" />
                <Button variant="ghost" size="icon" title="Retirer la signature" onClick={() => setSignature(null)}><X className="h-4 w-4" /></Button>
              </div>
            ) : (
              <label className="flex cursor-pointer flex-col items-center gap-2 text-center text-sm text-muted-foreground">
                <PenLine className="h-6 w-6 text-primary" />
                <span>Ajouter une image de signature PNG ou JPEG</span>
                <span className="flex items-center gap-1 text-xs"><Upload className="h-3 w-3" />2 Mo maximum</span>
                <input type="file" accept="image/png,image/jpeg" className="hidden" onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (!file) return;
                  if (file.size > 2 * 1024 * 1024) { onError("La signature dépasse 2 Mo"); return; }
                  const reader = new FileReader();
                  reader.onload = () => setSignature(String(reader.result));
                  reader.readAsDataURL(file);
                }} />
              </label>
            )}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">La signature est alignée automatiquement en bas à droite du PDF et n’est pas conservée séparément.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <Label htmlFor="inv-issue">Date d'émission</Label>
            <Input
              id="inv-issue"
              type="date"
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="inv-due">Échéance</Label>
            <Input
              id="inv-due"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="inv-currency">Devise</Label>
            <Select
              id="inv-currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              {options?.currencies.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.value}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="inv-tax">Taxes</Label>
            <Select
              id="inv-tax"
              value={taxRegime}
              onChange={(e) => setTaxRegime(e.target.value)}
            >
              {options?.tax_regimes.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div>
          <Label>Prestations</Label>
          <div className="space-y-2">
            {lines.map((line, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  className="flex-1"
                  value={line.description}
                  onChange={(e) => updateLine(index, { description: e.target.value })}
                  placeholder="Gestion Google Ads — septembre 2026"
                />
                <Input
                  className="w-20"
                  type="number"
                  min="0"
                  step="0.5"
                  value={line.quantity}
                  onChange={(e) => updateLine(index, { quantity: e.target.value })}
                  placeholder="Qté"
                />
                <Input
                  className="w-28"
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.unit_price}
                  onChange={(e) => updateLine(index, { unit_price: e.target.value })}
                  placeholder="Prix"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  title="Retirer la ligne"
                  disabled={lines.length === 1}
                  onClick={() => setLines((c) => c.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="mt-2"
            onClick={() => setLines((c) => [...c, { ...EMPTY_LINE }])}
          >
            <Plus className="h-3.5 w-3.5" />
            Ajouter une ligne
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="inv-discount">Remise (avant taxes)</Label>
            <Input
              id="inv-discount"
              type="number"
              min="0"
              step="0.01"
              value={discount}
              onChange={(e) => setDiscount(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="inv-notes">Notes sur la facture</Label>
            <Textarea
              id="inv-notes"
              className="min-h-[40px]"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Budget média facturé séparément par les régies."
            />
          </div>
        </div>

        <div className="rounded-xl bg-muted/50 p-4">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Sous-total</span>
            <span>{money(totals.subtotal)}</span>
          </div>
          {totals.taxes.map((t) => (
            <div key={t.label} className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t.label}</span>
              <span>{money(t.amount)}</span>
            </div>
          ))}
          <div className="mt-2 flex justify-between border-t border-border pt-2 font-semibold">
            <span>Total {currency}</span>
            <span className="text-primary">{money(totals.total)}</span>
          </div>
        </div>

        <Button className="w-full" size="lg" disabled={!canSubmit} onClick={submit}>
          <Receipt className="h-4 w-4" />
          {busy ? "Génération..." : "Générer la facture"}
        </Button>
      </CardContent>
    </Card>
  );
}
