import { BarChart3, CheckCircle2, Eye, KeyRound, Link2, Loader2, MousePointerClick, RefreshCw, Send, Target, Trash2, Upload, Users, WalletCards } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { AdvertisingKpis, AdvertisingPlatform, PlatformConnection, advertisingApi } from "@/features/advertising/api";
import { Client, clientsApi } from "@/features/clients/api";
import { PageHeader } from "@/shared/components/AppLayout";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/Card";
import { Input, Label, Select, Textarea } from "@/shared/components/ui/Field";

const PERIODS = [["today", "Aujourd’hui"], ["yesterday", "Hier"], ["last_7d", "7 jours"], ["last_14d", "14 jours"], ["last_30d", "30 jours"], ["this_month", "Ce mois-ci"]] as const;
const number = (value: number, digits = 0) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: digits }).format(value);
const money = (value: number, currency: string | null) => currency ? new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: 2 }).format(value) : number(value, 2);

export default function AdvertisingPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [platforms, setPlatforms] = useState<AdvertisingPlatform[]>([]);
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [active, setActive] = useState("meta");
  const [accountId, setAccountId] = useState("");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [period, setPeriod] = useState("last_30d");
  const [kpis, setKpis] = useState<AdvertisingKpis | null>(null);
  const [image, setImage] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const platform = platforms.find((item) => item.value === active);
  const connection = connections.find((item) => item.platform === active);
  const metaConnected = connections.some((item) => item.platform === "meta");

  useEffect(() => {
    Promise.all([clientsApi.list(), advertisingApi.platforms()])
      .then(([clientList, platformList]) => { setClients(clientList); setPlatforms(platformList); if (clientList[0]) setClientId(clientList[0].id); })
      .catch((e) => setError(e.message));
  }, []);

  const refreshConnections = async () => {
    if (!clientId) return;
    try { setConnections(await advertisingApi.connections(clientId)); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { void refreshConnections(); }, [clientId]);
  useEffect(() => { setAccountId(connection?.account_id ?? ""); setCredentials({}); setKpis(null); }, [active, connection?.account_id, clientId]);

  const loadKpis = async () => {
    if (!clientId || !connection) return;
    setBusy(true); setError(null);
    try { setKpis(await advertisingApi.platformKpis(active, clientId, period)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  useEffect(() => { if (connection) void loadKpis(); }, [active, period, connection?.account_id]);

  const save = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError(null); setSuccess(null);
    try {
      await advertisingApi.savePlatformConnection(active, { client_id: clientId, account_id: accountId, credentials });
      await refreshConnections(); setCredentials({}); setSuccess(`${platform?.label} connecté. Les secrets sont chiffrés.`);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!connection || !window.confirm(`Déconnecter ${connection.label} ?`)) return;
    setBusy(true);
    try { await advertisingApi.removePlatformConnection(active, clientId); await refreshConnections(); setKpis(null); setAccountId(""); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const publish = async (event: FormEvent) => {
    event.preventDefault(); if (!image) return; setBusy(true); setError(null);
    try { const result = await advertisingApi.publishInstagram(clientId, image, caption); setSuccess(`${result.message} · ${result.id}`); setImage(null); setCaption(""); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  const previewUrl = useMemo(() => image ? URL.createObjectURL(image) : null, [image]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  const cards = kpis ? [
    ["Dépenses", money(kpis.spend, kpis.currency), WalletCards], ["Impressions", number(kpis.impressions), Eye], ["Portée", number(kpis.reach), Users], ["Clics", number(kpis.clicks), MousePointerClick], ["CTR", `${number(kpis.ctr, 2)} %`, BarChart3], ["Conversions", number(kpis.conversions, 1), Target], ["CPC", money(kpis.cpc, kpis.currency), WalletCards], ["ROAS", `${number(kpis.purchase_roas, 2)}×`, RefreshCw],
  ] as const : [];

  return <div>
    <PageHeader title="Publicité" description="Connectez les régies par client, consultez leurs KPI réels et utilisez-les dans les rapports." action={<div><Label htmlFor="ads-client">Client</Label><Select id="ads-client" className="min-w-52" value={clientId} onChange={(e) => setClientId(e.target.value)}>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</Select></div>} />
    {error && <div className="mb-5 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">{error}</div>}
    {success && <div className="mb-5 rounded-xl border border-success/20 bg-success/5 px-4 py-3 text-sm text-success">{success}</div>}

    <Card className="mb-6"><CardHeader><CardTitle className="flex items-center gap-2"><Link2 className="h-5 w-5 text-primary" />Connexions disponibles</CardTitle><CardDescription>Cliquez sur une régie pour ajouter ou modifier sa connexion.</CardDescription></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{platforms.map((item) => { const linked = connections.some((saved) => saved.platform === item.value); return <button key={item.value} type="button" onClick={() => setActive(item.value)} className={`rounded-xl border p-4 text-left transition ${active === item.value ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}><div className="mb-2 flex items-center justify-between"><KeyRound className="h-4 w-4 text-primary" />{linked && <CheckCircle2 className="h-4 w-4 text-success" />}</div><p className="text-sm font-semibold">{item.label}</p><p className="mt-1 text-xs text-muted-foreground">{linked ? "Connecté" : "Ajouter"}</p></button>; })}</div></CardContent></Card>

    <div className="grid gap-6 lg:grid-cols-[390px_1fr]">
      <Card><CardHeader><CardTitle>{platform?.label ?? "Connexion"}</CardTitle><CardDescription>{platform?.description}</CardDescription></CardHeader><CardContent><form className="space-y-4" onSubmit={save}><div><Label htmlFor="platform-account">ID du compte publicitaire</Label><Input id="platform-account" required value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder="Identifiant fourni par la régie" /></div>{platform?.credential_fields.map((field) => <div key={field.key}><Label htmlFor={`credential-${field.key}`}>{field.label}</Label><Input id={`credential-${field.key}`} type={field.secret ? "password" : "text"} required={field.required && !connection?.configured_fields.includes(field.key)} value={credentials[field.key] ?? ""} onChange={(e) => setCredentials((current) => ({ ...current, [field.key]: e.target.value }))} placeholder={connection?.configured_fields.includes(field.key) ? "Déjà enregistré — laisser vide pour conserver" : field.placeholder} autoComplete="off" />{field.help && <p className="mt-1 text-xs text-muted-foreground">{field.help}</p>}</div>)}<p className="rounded-lg bg-muted p-3 text-xs text-muted-foreground">Les jetons sont chiffrés côté serveur et ne sont jamais renvoyés au navigateur ni à n8n.</p><div className="flex gap-2"><Button className="flex-1" type="submit" disabled={busy || !clientId}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}{connection ? "Mettre à jour" : "Connecter"}</Button>{connection && <Button variant="ghost" type="button" onClick={remove} disabled={busy} title="Déconnecter"><Trash2 className="h-4 w-4" /></Button>}</div></form></CardContent></Card>

      <Card><CardHeader className="flex flex-row items-start justify-between gap-4"><div><CardTitle>KPI {platform?.label}</CardTitle><CardDescription>Données consolidées au niveau du compte.</CardDescription></div><div className="flex gap-2"><Select className="w-36" value={period} onChange={(e) => setPeriod(e.target.value)}>{PERIODS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select><Button variant="secondary" size="icon" disabled={!connection || busy} onClick={() => void loadKpis()}><RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} /></Button></div></CardHeader><CardContent>{!connection ? <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">Connectez cette régie pour afficher ses données réelles.</div> : busy && !kpis ? <Loader2 className="mx-auto h-5 w-5 animate-spin" /> : <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{cards.map(([label, value, Icon]) => <div key={label} className="rounded-xl border border-border bg-muted/30 p-4"><div className="mb-3 flex items-center justify-between"><span className="text-xs text-muted-foreground">{label}</span><Icon className="h-4 w-4 text-primary" /></div><p className="text-xl font-bold">{value}</p></div>)}</div>}</CardContent></Card>
    </div>

    {metaConnected && <Card className="mt-6"><CardHeader><CardTitle>Publier sur Instagram</CardTitle><CardDescription>Publication immédiate sur le compte professionnel Meta connecté.</CardDescription></CardHeader><CardContent><form className="grid gap-5 lg:grid-cols-[300px_1fr]" onSubmit={publish}><label className="flex min-h-48 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-border bg-muted/30">{previewUrl ? <img src={previewUrl} alt="Aperçu" className="max-h-64 w-full object-contain" /> : <><Upload className="mb-2 h-7 w-7 text-muted-foreground" /><span className="text-sm text-muted-foreground">JPEG ou PNG</span></>}<input type="file" accept="image/jpeg,image/png" className="hidden" onChange={(e) => setImage(e.target.files?.[0] ?? null)} /></label><div><Label htmlFor="caption">Légende</Label><Textarea id="caption" className="min-h-36" required maxLength={2200} value={caption} onChange={(e) => setCaption(e.target.value)} /><Button className="mt-3" disabled={!image || !caption || busy} type="submit"><Send className="h-4 w-4" />Publier</Button></div></form></CardContent></Card>}
  </div>;
}
