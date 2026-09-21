import { useEffect, useRef, useState } from "react";
import { autoReviewApi } from "@/features/auto-review/api";
import { Client, clientsApi } from "@/features/clients/api";
import ClientCreateForm from "@/features/clients/ClientCreateForm";
import { DataFile, dataApi } from "@/features/data/api";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Input, Label, Select, Textarea } from "@/shared/components/ui/Field";

export default function ReviewForm({ onLaunched, onError }: { onLaunched: () => void; onError: (message: string) => void }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [files, setFiles] = useState<DataFile[]>([]);
  const [clientId, setClientId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);
  useEffect(() => { clientsApi.list().then(list => { setClients(list); setClientId(list[0]?.id || ""); }).catch(e => onError(e.message)); }, []);
  useEffect(() => {
    let active = true;
    setFiles([]); setSelected([]);
    if (!clientId) return;
    setLoading(true);
    dataApi.listFiles(clientId).then(list => { if (active) setFiles(list); })
      .catch(e => { if (active) onError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [clientId]);
  async function upload(list: File[]) {
    if (!list.length || !clientId || busy || loading) return;
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period)) { onError("Choisis la période des fichiers."); return; }
    if (list.some(file => !/\.xlsx$/i.test(file.name))) { onError("Le workflow actuel accepte uniquement les fichiers Excel .xlsx."); return; }
    setBusy(true);
    try {
      const created = await dataApi.upload(clientId, period, list);
      setFiles(current => [...current, ...created]);
      setSelected(current => [...current, ...created.map(f => f.id)]);
    } catch(e) { onError((e as Error).message); }
    finally { setBusy(false); if (uploadRef.current) uploadRef.current.value = ""; }
  }
  async function submit() {
    if (!clientId || !selected.length || busy || loading) return;
    setBusy(true);
    try {
      await autoReviewApi.launch({client_id:clientId, client_type:clients.find(c => c.id === clientId)?.client_type || "other", data_file_ids:selected, selected_platforms:[], additional_info:info || null});
      setSelected([]); setInfo(""); onLaunched();
    } catch(e) { onError((e as Error).message); }
    finally { setBusy(false); }
  }
  const eligible = files.filter(f => /\.xlsx$/i.test(f.filename));
  return <Card><CardContent className="space-y-5 p-6">
    <ClientCreateForm disabled={busy || loading} onCreated={c => { setClients(list => [...list,c]); setClientId(c.id); }} />
    <div><Label htmlFor="review-client">Client</Label><Select id="review-client" disabled={busy || loading} value={clientId} onChange={e => setClientId(e.target.value)}>
      {!clients.length && <option value="">Crée d’abord un client</option>}
      {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
    </Select></div>
    <div><Label htmlFor="review-period">Période des nouveaux fichiers</Label><Input id="review-period" type="month" disabled={busy} value={period} onChange={e => setPeriod(e.target.value)} /></div>
    <div className={`rounded-xl border-2 border-dashed p-5 text-center ${drag ? "border-primary bg-primary-soft" : "border-border"}`}
      onDragOver={e => { e.preventDefault(); if (clientId && !busy && !loading) setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); void upload(Array.from(e.dataTransfer.files)); }}>
      <p className="mb-3 text-sm">Glisse-dépose tes fichiers Excel ici</p>
      <input ref={uploadRef} type="file" accept=".xlsx" multiple className="hidden" onChange={e => void upload(Array.from(e.target.files || []))} />
      <Button variant="secondary" disabled={!clientId || busy || loading} onClick={() => uploadRef.current?.click()}>{busy ? "Traitement…" : "Choisir des fichiers"}</Button>
    </div>
    <p className="text-xs text-muted-foreground">Rapports : Excel .xlsx uniquement, première feuille, échantillon de 30 lignes. Les sources publicitaires ne sont pas encore intégrées au workflow.</p>
    {loading ? <p role="status">Chargement des fichiers…</p> : <>
      <div className="flex gap-2"><Button size="sm" variant="ghost" disabled={busy || !eligible.length} onClick={() => setSelected(eligible.map(f => f.id))}>Tout sélectionner</Button><Button size="sm" variant="ghost" disabled={busy || !selected.length} onClick={() => setSelected([])}>Tout désélectionner</Button></div>
      <div className="max-h-60 overflow-y-auto">
        {!files.length && <p className="text-sm text-muted-foreground">Aucun fichier pour ce client.</p>}
        {files.map(f => <label key={f.id} className="flex items-center gap-3 border-b border-border py-3">
          <input type="checkbox" disabled={busy || !/\.xlsx$/i.test(f.filename)} checked={selected.includes(f.id)} onChange={() => setSelected(ids => ids.includes(f.id) ? ids.filter(id => id !== f.id) : [...ids,f.id])} />
          <span className="min-w-0 text-sm"><span className="block truncate">{f.filename}</span><span className="text-xs text-muted-foreground">{f.period}{!/\.xlsx$/i.test(f.filename) && " — format non pris en charge"}</span></span>
        </label>)}
      </div>
    </>}
    <div><Label htmlFor="review-info">Instructions facultatives</Label><Textarea id="review-info" value={info} maxLength={2000} disabled={busy} onChange={e => setInfo(e.target.value)} /></div>
    <Button className="w-full" disabled={!clientId || !selected.length || busy || loading} onClick={submit}>{busy ? "Préparation…" : `Générer le rapport (${selected.length} fichier(s))`}</Button>
  </CardContent></Card>;
}
