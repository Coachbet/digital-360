import { Building2, CheckCircle2, Download, Receipt } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Invoice, Option, invoicingApi } from "@/features/invoicing/api";
import InvoiceForm from "@/features/invoicing/components/InvoiceForm";
import { PageHeader } from "@/shared/components/AppLayout";
import { Badge, BadgeTone } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";

const STATUS_TONE: Record<string, BadgeTone> = {
  draft: "neutral",
  issued: "primary",
  paid: "success",
  cancelled: "danger",
};

export default function InvoicingPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [statuses, setStatuses] = useState<Option[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    invoicingApi
      .list()
      .then(setInvoices)
      .catch((e) => setError(e.message));

  useEffect(() => {
    refresh();
    invoicingApi
      .options()
      .then((o) => setStatuses(o.statuses))
      .catch(() => undefined);
  }, []);

  const download = async (invoice: Invoice) => {
    try {
      const { url } = await invoicingApi.pdfUrl(invoice.id);
      window.open(url, "_blank");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const markPaid = async (invoice: Invoice) => {
    try {
      await invoicingApi.setStatus(invoice.id, "paid");
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const money = (value: string, currency: string) =>
    Number(value).toLocaleString("fr-CA", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + (currency === "EUR" ? " €" : " $");

  return (
    <div>
      <PageHeader
        title="Facturation"
        description="Saisissez les prestations : la facture est générée en PDF aux couleurs de votre agence, avec vos mentions légales."
        action={
          <Link to="/agence">
            <Button variant="secondary">
              <Building2 className="h-4 w-4" />
              Coordonnées de l'agence
            </Button>
          </Link>
        }
      />

      {error && (
        <div className="mb-6 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,520px)_1fr]">
        <InvoiceForm onCreated={refresh} onError={setError} />

        <div>
          <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
            Factures ({invoices.length})
          </h2>

          {invoices.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-2 p-16 text-center">
                <Receipt className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Aucune facture émise</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {invoices.map((invoice) => (
                <Card key={invoice.id}>
                  <CardContent className="flex flex-wrap items-center gap-4 p-5">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-primary">{invoice.number}</p>
                        <Badge tone={STATUS_TONE[invoice.status] ?? "neutral"}>
                          {statuses.find((s) => s.value === invoice.status)?.label ??
                            invoice.status}
                        </Badge>
                      </div>
                      <p className="mt-0.5 truncate text-sm">{invoice.client_name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Émise le{" "}
                        {new Date(invoice.issue_date).toLocaleDateString("fr-FR")}
                        {invoice.due_date &&
                          ` · échéance ${new Date(invoice.due_date).toLocaleDateString("fr-FR")}`}
                      </p>
                    </div>

                    <p className="text-lg font-bold">
                      {money(invoice.total, invoice.currency)}
                    </p>

                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" onClick={() => download(invoice)}>
                        <Download className="h-3.5 w-3.5" />
                        PDF
                      </Button>
                      {invoice.status === "issued" && (
                        <Button size="sm" onClick={() => markPaid(invoice)}>
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Payée
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
