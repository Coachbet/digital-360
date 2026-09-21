import { useState, type FormEvent } from "react";
import { Client, clientsApi } from "./api";
import { Button } from "@/shared/components/ui/Button";
import { Input, Label, Select } from "@/shared/components/ui/Field";

export default function ClientCreateForm({ onCreated, disabled = false }: { onCreated: (client: Client) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [type, setType] = useState("ecommerce");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || disabled || !name.trim()) return;
    setBusy(true); setError("");
    try {
      const client = await clientsApi.create({ name: name.trim(), client_type: type, contact_email: email.trim() || null });
      onCreated(client); setOpen(false); setName(""); setEmail("");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <div className="space-y-3">
    <Button variant="secondary" disabled={busy || disabled} onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Fermer" : "+ Ajouter un client"}</Button>
    {open && <form onSubmit={submit} className="space-y-3 rounded-xl border border-border bg-card p-4">
      <h2 className="font-semibold">Nouveau client</h2>
      <Label>Nom du client<Input autoFocus required maxLength={200} value={name} disabled={busy} onChange={e => setName(e.target.value)} placeholder="Boutique Demo Boreale" /></Label>
      <Label>Courriel de contact (facultatif)<Input type="email" value={email} disabled={busy} onChange={e => setEmail(e.target.value)} /></Label>
      <Label>Activité<Select value={type} disabled={busy} onChange={e => setType(e.target.value)}>
        {Object.entries({ ecommerce: "E-commerce", b2b: "B2B", lead_gen: "Génération de leads", marketplace: "Marketplace", local: "Commerce local", brand: "Marque", other: "Autre" }).map(([value,label]) => <option key={value} value={value}>{label}</option>)}
      </Select></Label>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <Button type="submit" disabled={busy || disabled || !name.trim()}>{busy ? "Création…" : "Créer le client"}</Button>
    </form>}
  </div>;
}
