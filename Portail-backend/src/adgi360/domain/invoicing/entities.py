"""Cœur métier de la facturation : devises, régimes de taxes et calculs.

Aucune dépendance technique ici — ces règles sont testables seules et
réutilisables si le rendu PDF change un jour.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


def _money(value: Decimal | float | str) -> Decimal:
    """Arrondi monétaire à 2 décimales, au demi supérieur (règle comptable)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Currency(str, Enum):
    CAD = "CAD"
    USD = "USD"
    EUR = "EUR"

    @property
    def symbol(self) -> str:
        return {Currency.CAD: "$", Currency.USD: "$", Currency.EUR: "€"}[self]

    @property
    def label(self) -> str:
        return {
            Currency.CAD: "Dollar canadien (CAD)",
            Currency.USD: "Dollar américain (USD)",
            Currency.EUR: "Euro (EUR)",
        }[self]


class TaxRegime(str, Enum):
    """Régimes fiscaux proposés. Les taux sont ceux en vigueur au Québec et en
    France ; ils sont figés ici volontairement pour que le calcul soit
    reproductible et vérifiable sur une facture archivée."""

    QC_GST_QST = "qc_gst_qst"   # Québec : TPS 5 % + TVQ 9,975 %
    GST_ONLY = "gst_only"        # Canada hors Québec : TPS 5 %
    EU_VAT_20 = "eu_vat_20"      # France : TVA 20 %
    NONE = "none"                 # Hors taxes

    @property
    def label(self) -> str:
        return {
            TaxRegime.QC_GST_QST: "Québec — TPS 5 % + TVQ 9,975 %",
            TaxRegime.GST_ONLY: "Canada — TPS 5 %",
            TaxRegime.EU_VAT_20: "France — TVA 20 %",
            TaxRegime.NONE: "Hors taxes",
        }[self]

    @property
    def taxes(self) -> list[tuple[str, Decimal]]:
        """Liste (libellé, taux) appliquée au sous-total."""
        return {
            TaxRegime.QC_GST_QST: [
                ("TPS (5 %)", Decimal("0.05")),
                ("TVQ (9,975 %)", Decimal("0.09975")),
            ],
            TaxRegime.GST_ONLY: [("TPS (5 %)", Decimal("0.05"))],
            TaxRegime.EU_VAT_20: [("TVA (20 %)", Decimal("0.20"))],
            TaxRegime.NONE: [],
        }[self]


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        return {
            InvoiceStatus.DRAFT: "Brouillon",
            InvoiceStatus.ISSUED: "Émise",
            InvoiceStatus.PAID: "Payée",
            InvoiceStatus.CANCELLED: "Annulée",
        }[self]


@dataclass
class InvoiceLine:
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def total(self) -> Decimal:
        return _money(self.quantity * self.unit_price)


@dataclass
class InvoiceTotals:
    subtotal: Decimal
    taxes: list[tuple[str, Decimal]]
    total: Decimal


@dataclass
class Invoice:
    """Entité de domaine d'une facture."""

    id: str
    number: str
    client_name: str
    lines: list[InvoiceLine] = field(default_factory=list)
    currency: Currency = Currency.CAD
    tax_regime: TaxRegime = TaxRegime.QC_GST_QST
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: date | None = None
    due_date: date | None = None
    client_address: str | None = None
    client_email: str | None = None
    notes: str | None = None
    discount: Decimal = Decimal("0")

    def compute(self) -> InvoiceTotals:
        """Sous-total, taxes ligne par ligne, puis total.

        La remise s'applique avant les taxes : c'est la règle usuelle, et c'est
        ce qui permet aux taxes affichées de correspondre au montant réellement
        facturé.
        """
        gross = sum((line.total for line in self.lines), Decimal("0"))
        subtotal = _money(gross - self.discount)
        if subtotal < 0:
            subtotal = Decimal("0.00")

        taxes = [(label, _money(subtotal * rate)) for label, rate in self.tax_regime.taxes]
        total = _money(subtotal + sum((amount for _, amount in taxes), Decimal("0")))
        return InvoiceTotals(subtotal=subtotal, taxes=taxes, total=total)


def build_invoice_number(year: int, sequence: int, prefix: str = "F") -> str:
    """Numérotation séquentielle par année et par agence : F-2026-0001.

    Les factures doivent être numérotées sans rupture de séquence ; la séquence
    est calculée à partir du nombre de factures déjà émises dans l'année par
    cette agence. Le préfixe est neutre : chaque organisation garde sa propre
    série, sans marque codée en dur dans le produit.
    """
    return f"{prefix}-{year}-{sequence:04d}"
