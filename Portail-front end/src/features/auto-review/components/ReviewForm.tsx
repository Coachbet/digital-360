import { Database, Link2, Sparkles, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { autoReviewApi } from "@/features/auto-review/api";
import { AdvertisingPlatform, PlatformConnection, advertisingApi } from "@/features/advertising/api";
import { Client, clientsApi } from "@/features/clients/api";
import { DataFile, dataApi } from "@/features/data/api";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Label, Select, Textarea } from "@/shared/components/ui/Field";
import { formatBytes } from "@/shared/lib/utils";

const currentPeriod = () => new Date().toISOString().slice(0, 7);

export default function ReviewForm({ onLaunched, onError }: { onLaunched: () => void; onError: (message: string) => void }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [files, setFiles] = useState<DataFile[]>([]);
  const [platforms, setPlatforms] = useState<AdvertisingPlatform[]>([]);
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [clientId, setClientId] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([clientsApi.list(), advertisingApi.platforms()])
      .then(([clientList, platformList]) => {
        setClients(clientList);
        setPlatforms(platformList);
        if (clientList[0]) setClientId(clientList[0].id);
      })
      .catch((e) => onError(e.message));
  }, []);

  const refreshSources = async (id: string) => {
    if (!id) return;
    try {
      const [externalFiles, connected] = await Promise.all([dataApi.listFiles(id), advertisingApi.connections(id)]);
      setFiles(externalFiles);
      setConnections(connected);
    } catch (e) {
      onError((e as Error).message);
    }
  };

  useEffect(() => {
    setSelectedFiles([]);
    setSelectedPlatforms([]);
    void refreshSources(clientId);
  }, [clientId]);

  const upload = async (list: FileList | null) => {
    if (!list?.length || !clientId) return;
    setBusy(true);
    try {
      const created = await dataApi.upload(clientId, currentPeriod(), list);
      await refreshSources(clientId);
      setSelectedFiles((current) => [...new Set([...current, ...created.map((file) => file.id)])]);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
      if (uploadRef.current) uploadRef.current.value = "";
    }
  };

  const toggle = (value: string, selected: string[], setter: (values: string[]) => void) =>
    setter(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);

  const submit = async () => {
    setBusy(true);
    try {
      await autoReviewApi.launch({ client_id: clientId, data_file_ids: selectedFiles, selected_platforms: selectedPlatforms, additional_info: info || null });
      setSelectedFiles([]);
      setSelectedPlatforms([]);
      setInfo("");
      onLaunched();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const canSubmit = clientId && (selectedFiles.length > 0 || selectedPlatforms.length > 0) && !busy;

  return (
    <Card className="h-fit">
      <CardContent className="space-y-5 p-6">
        <div>
          <Label htmlFor="review-client">Client</Label>
          <Select id="review-client" value={clientId} onChange={(event) => setClientId(event.target.value)}>
            {clients.length === 0 && <option value="">Aucun client</option>}
            {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
          </Select>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <Label><Database className="mr-1 inline h-3.5 w-3.5" />Documents externes</Label>
            <Button variant="secondary" size="sm" disabled={!clientId || busy} onClick={() => uploadRef.current?.click()}><Upload className="h-3.5 w-3.5" /> Ajouter</Button>
            <input ref={uploadRef} type="file" multiple className="hidden" onChange={(event) => void upload(event.target.files)} />
          </div>
          <div className="max-h-52 overflow-y-auto rounded-xl border border-border">
            {files.length === 0 ? <p className="p-4 text-center text-xs text-muted-foreground">Ajoutez un document CSV, Excel, PDF ou PowerPoint.</p> : files.map((file) => (
              <label key={file.id} className="flex cursor-pointer items-center gap-3 border-b border-border px-3 py-2.5 last:border-0 hover:bg-muted/50">
                <input type="checkbox" checked={selectedFiles.includes(file.id)} onChange={() => toggle(file.id, selectedFiles, setSelectedFiles)} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                <span className="min-w-0 flex-1"><span className="block truncate text-sm">{file.filename}</span><span className="block text-xs text-muted-foreground">{file.period} · {formatBytes(file.size_bytes)}</span></span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <Label><Link2 className="mr-1 inline h-3.5 w-3.5" />Données des plateformes</Label>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {platforms.map((platform) => {
              const connected = connections.some((item) => item.platform === platform.value);
              return <label key={platform.value} className={`flex items-center gap-3 rounded-xl border p-3 ${connected ? "cursor-pointer border-border hover:bg-muted/40" : "cursor-not-allowed opacity-50"}`}>
                <input type="checkbox" disabled={!connected} checked={selectedPlatforms.includes(platform.value)} onChange={() => toggle(platform.value, selectedPlatforms, setSelectedPlatforms)} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                <span className="min-w-0"><span className="block text-sm font-medium">{platform.label}</span><span className="block text-xs text-muted-foreground">{connected ? "Connexion prête" : "À connecter dans Publicité"}</span></span>
              </label>;
            })}
          </div>
        </div>

        <div><Label htmlFor="review-info">Instructions facultatives</Label><Textarea id="review-info" value={info} onChange={(event) => setInfo(event.target.value)} placeholder="Points à mettre en avant, période, ton du rapport…" /></div>
        <Button className="w-full" size="lg" disabled={!canSubmit} onClick={submit}><Sparkles className="h-4 w-4" />{busy ? "Préparation…" : "Générer le rapport"}</Button>
      </CardContent>
    </Card>
  );
}
