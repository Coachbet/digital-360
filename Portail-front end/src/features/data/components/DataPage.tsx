import { Download, FileText, FolderPlus, Trash2, Upload } from "lucide-react";
import { type DragEvent, useEffect, useRef, useState } from "react";

import { Client, clientsApi } from "@/features/clients/api";
import ClientCreateForm from "@/features/clients/ClientCreateForm";
import { DataFile, Period, dataApi } from "@/features/data/api";
import { PageHeader } from "@/shared/components/AppLayout";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Badge } from "@/shared/components/ui/Badge";
import { Input, Label, Select } from "@/shared/components/ui/Field";
import { formatBytes } from "@/shared/lib/utils";

/** Période par défaut au format AAAA-MM. */
function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function DataPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState("");
  const [periods, setPeriods] = useState<Period[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<string>("");
  const [files, setFiles] = useState<DataFile[]>([]);
  const [uploadPeriod, setUploadPeriod] = useState(currentPeriod);
  const [busy, setBusy] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);
  const requestId = useRef(0);

  useEffect(() => {
    clientsApi
      .list()
      .then((list) => {
        setClients(list);
        if (list.length > 0) setClientId((current) => current || list[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const refresh = async (id: string, period: string) => {
    if (!id) return;
    const request = ++requestId.current;
    const [p, f] = await Promise.all([
      dataApi.listPeriods(id),
      dataApi.listFiles(id, period || undefined),
    ]);
    if (request === requestId.current) { setPeriods(p); setFiles(f); }
  };

  useEffect(() => {
    setFiles([]);
    if (clientId) refresh(clientId, selectedPeriod).catch((e) => setError(e.message));
    return () => { requestId.current += 1; };
  }, [clientId, selectedPeriod]);

  const handleUpload = async (list: FileList | File[] | null) => {
    if (!list || list.length === 0 || !clientId || busy) return;
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(uploadPeriod)) { setError("Choisis une période au format AAAA-MM."); return; }
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await dataApi.upload(clientId, uploadPeriod, list);
      await refresh(clientId, selectedPeriod);
      setNotice(`${list.length} fichier(s) ajouté(s) pour ${uploadPeriod}.`);
      if (fileInput.current) fileInput.current.value = "";
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleDragEnter = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current += 1;
    if (!busy && uploadPeriod) setIsDragging(true);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = busy || !uploadPeriod ? "none" : "copy";
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setIsDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current = 0;
    setIsDragging(false);
    if (busy || !uploadPeriod) return;
    void handleUpload(Array.from(event.dataTransfer.files));
  };

  const handleDownload = async (file: DataFile) => {
    try { const { url } = await dataApi.downloadUrl(file.id); window.location.assign(url); }
    catch (e) { setError((e as Error).message); }
  };

  const handleDelete = async (file: DataFile) => {
    if (!window.confirm(`Supprimer le fichier « ${file.filename} » ?`)) return;
    setBusy(true);
    try {
      await dataApi.remove(file.id);
      await refresh(clientId, selectedPeriod);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Données"
        description="Les fichiers sources de chaque client, rangés par période. C'est ici qu'on dépose ce que l'Auto Review utilisera."
      />

      {error && (
        <div className="mb-6 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="mb-6"><ClientCreateForm disabled={busy || loading} onCreated={client => { setClients(current => [...current, client]); setClientId(client.id); setSelectedPeriod(""); setError(null); setNotice(`Client « ${client.name} » créé.`); }} /></div>
      {notice && <p role="status" className="mb-4 text-sm text-success">{notice}</p>}
      {loading ? <p role="status">Chargement des clients…</p> : clients.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
            <FolderPlus className="h-8 w-8 text-muted-foreground" />
            <p className="font-medium">Aucun client enregistré</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Crée d'abord un client pour pouvoir y déposer des fichiers.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <div className="space-y-6">
            <Card>
              <CardContent className="space-y-4 p-5">
                <div>
                  <Label htmlFor="client">Client</Label>
                  <Select
                    id="client"
                    value={clientId}
                    disabled={busy}
                    onChange={(e) => {
                      setClientId(e.target.value);
                      setSelectedPeriod("");
                    }}
                  >
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </Select>
                </div>

                <div>
                  <Label>Périodes</Label>
                  <div className="space-y-1">
                    <button
                      disabled={busy}
                      onClick={() => setSelectedPeriod("")}
                      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                        selectedPeriod === ""
                          ? "bg-primary-soft text-primary"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      Toutes
                      <span className="text-xs">
                        {periods.reduce((sum, p) => sum + p.file_count, 0)}
                      </span>
                    </button>
                    {periods.map((p) => (
                      <button
                        disabled={busy}
                        key={p.period}
                        onClick={() => setSelectedPeriod(p.period)}
                        className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                          selectedPeriod === p.period
                            ? "bg-primary-soft text-primary"
                            : "text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        {p.period}
                        <span className="text-xs">{p.file_count}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="space-y-3 p-5">
                <Label htmlFor="period">Déposer dans la période</Label>
                <Input
                  id="period"
                  type="month"
                  disabled={busy}
                  value={uploadPeriod}
                  onChange={(e) => setUploadPeriod(e.target.value)}
                  placeholder="2026-08"
                />
                <div
                  className={`rounded-xl border-2 border-dashed px-4 py-6 text-center transition-colors ${
                    isDragging
                      ? "border-primary bg-primary-soft"
                      : "border-border bg-muted/30 hover:border-primary/50 hover:bg-muted/50"
                  } ${busy || !uploadPeriod ? "cursor-not-allowed opacity-60" : ""}`}
                  onDragEnter={handleDragEnter}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <Upload
                    className={`mx-auto mb-2 h-7 w-7 ${
                      isDragging ? "text-primary" : "text-muted-foreground"
                    }`}
                  />
                  <p
                    className={`text-sm ${
                      isDragging ? "font-medium text-primary" : "text-muted-foreground"
                    }`}
                  >
                    {isDragging
                      ? "Dépose les fichiers ici"
                      : "Glisse-dépose tes fichiers ici"}
                  </p>
                  <p className="my-2 text-xs text-muted-foreground">ou</p>
                  <input
                    ref={fileInput}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => handleUpload(e.target.files)}
                  />
                  <Button
                    className="w-full"
                    disabled={busy || !uploadPeriod}
                    onClick={() => fileInput.current?.click()}
                  >
                    <Upload className="h-4 w-4" />
                    {busy ? "Envoi..." : "Choisir des fichiers"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="p-4"><Input aria-label="Rechercher un fichier" placeholder="Rechercher un fichier…" value={search} onChange={e => setSearch(e.target.value)} /></div>
              {files.length > 0 && !files.some(file => file.filename.toLocaleLowerCase().includes(search.toLocaleLowerCase())) && <p className="p-6 text-sm text-muted-foreground">Aucun fichier ne correspond à cette recherche.</p>}
              {files.length === 0 ? (
                <div className="flex flex-col items-center gap-2 p-16 text-center">
                  <FileText className="h-8 w-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Aucun fichier {selectedPeriod && `pour ${selectedPeriod}`}
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {files.filter(file => file.filename.toLocaleLowerCase().includes(search.toLocaleLowerCase())).map((file) => (
                    <li
                      key={file.id}
                      className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-muted/50"
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{file.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatBytes(file.size_bytes)} ·{" "}
                          {new Date(file.uploaded_at).toLocaleDateString("fr-FR")}
                        </p>
                      </div>
                      <Badge>{file.period}</Badge>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Télécharger"
                          onClick={() => handleDownload(file)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Supprimer"
                          disabled={busy}
                          onClick={() => handleDelete(file)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
