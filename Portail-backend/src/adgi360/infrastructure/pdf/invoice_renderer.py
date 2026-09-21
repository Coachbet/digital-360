"""Rendu PDF des factures, aux couleurs de l'agence émettrice.

ReportLab est utilisé plutôt qu'un moteur HTML→PDF (WeasyPrint) parce qu'il est
pur Python : aucune dépendance système à installer sur les postes de l'équipe.

Le gabarit est construit en dessin direct sur le canevas plutôt qu'en flux
Platypus : une facture a une mise en page fixe, et le contrôle au point près
donne un rendu plus soigné.
"""

import io
from datetime import date
from decimal import Decimal

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from adgi360.domain.invoicing.entities import Invoice, InvoiceTotals

# Couleurs neutres, communes à toutes les agences
MUTED = HexColor("#6B7280")
HAIRLINE = HexColor("#E4E6EB")

# Repli quand une agence n'a pas encore choisi sa charte
DEFAULT_PRIMARY = "#6C4CF1"
DEFAULT_INK = "#171633"


def _soften(color: HexColor, amount: float = 0.92) -> Color:
    """Version très claire d'une couleur, pour les fonds de lignes alternées.

    Calculé plutôt que codé en dur : la teinte douce suit automatiquement la
    couleur choisie par l'agence, quelle qu'elle soit.
    """
    return Color(
        color.red + (1 - color.red) * amount,
        color.green + (1 - color.green) * amount,
        color.blue + (1 - color.blue) * amount,
    )

PAGE_W, PAGE_H = A4
MARGIN = 45


def _fmt(amount: Decimal, symbol: str) -> str:
    """1234.5 -> « 1 234,50 $ » : séparateur de milliers et virgule décimale.

    Espace ordinaire volontairement : Helvetica ne contient pas l'espace fine
    insécable (U+202F), qui se rendrait en carré noir dans le PDF.
    """
    entier, _, decimales = f"{amount:.2f}".partition(".")
    negatif = entier.startswith("-")
    entier = entier.lstrip("-")
    groupes = []
    while len(entier) > 3:
        groupes.insert(0, entier[-3:])
        entier = entier[:-3]
    groupes.insert(0, entier)
    return f"{'-' if negatif else ''}{' '.join(groupes)},{decimales} {symbol}"


def _fr_date(value: date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d/%m/%Y")


class InvoiceRenderer:
    def __init__(self, invoice: Invoice, totals: InvoiceTotals, company: dict) -> None:
        self.invoice = invoice
        self.totals = totals
        self.company = company
        self.primary = HexColor(company.get("brand_primary") or DEFAULT_PRIMARY)
        self.ink = HexColor(company.get("brand_ink") or DEFAULT_INK)
        self.soft = _soften(self.primary)

    def render(
        self,
        logo_bytes: bytes | None = None,
        signature_bytes: bytes | None = None,
    ) -> bytes:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setTitle(f"Facture {self.invoice.number}")
        c.setAuthor(self.company.get("legal_name") or "Digital 360")

        y = self._header(c, logo_bytes)
        y = self._parties(c, y)
        y = self._lines_table(c, y)
        y = self._totals(c, y)
        self._notes(c, y)
        self._signature(c, signature_bytes)
        self._footer(c)

        c.showPage()
        c.save()
        return buffer.getvalue()

    # ---------------------------------------------------------------- header

    def _header(self, c: canvas.Canvas, logo_bytes: bytes | None) -> float:
        # Bandeau magenta plein en haut de page
        c.setFillColor(self.primary)
        c.rect(0, PAGE_H - 8, PAGE_W, 8, stroke=0, fill=1)

        top = PAGE_H - 60

        if logo_bytes:
            try:
                image = ImageReader(io.BytesIO(logo_bytes))
                iw, ih = image.getSize()
                height = 38
                width = height * (iw / ih)
                c.drawImage(
                    image, MARGIN, top - height + 20, width=width, height=height,
                    mask="auto", preserveAspectRatio=True,
                )
            except Exception:
                self._wordmark(c, top)
        else:
            self._wordmark(c, top)

        c.setFont("Helvetica", 8.5)
        c.setFillColor(MUTED)
        c.drawString(MARGIN, top - 6, self.company.get("tagline", ""))

        # Bloc « FACTURE » aligné à droite
        c.setFont("Helvetica-Bold", 26)
        c.setFillColor(self.ink)
        c.drawRightString(PAGE_W - MARGIN, top + 12, "FACTURE")

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.primary)
        c.drawRightString(PAGE_W - MARGIN, top - 6, self.invoice.number)

        c.setFont("Helvetica", 8.5)
        c.setFillColor(MUTED)
        c.drawRightString(
            PAGE_W - MARGIN, top - 20, f"Émise le {_fr_date(self.invoice.issue_date)}"
        )
        if self.invoice.due_date:
            c.drawRightString(
                PAGE_W - MARGIN, top - 32, f"Échéance le {_fr_date(self.invoice.due_date)}"
            )

        return top - 58

    def _wordmark(self, c: canvas.Canvas, top: float) -> None:
        """Nom de l'agence en typographie, quand aucun logo n'a été téléversé.

        Si le nom se termine par un nombre (« Agence 360 »), ce suffixe est
        coloré à l'accent de la marque : un rappel visuel simple qui fonctionne
        pour n'importe quelle agence, sans rien coder en dur.
        """
        name = self.company.get("legal_name") or "Agence"
        head, tail = name, ""
        parts = name.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            head, tail = parts[0] + " ", parts[1]

        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(self.ink)
        c.drawString(MARGIN, top + 8, head)
        if tail:
            width = c.stringWidth(head, "Helvetica-Bold", 20)
            c.setFillColor(self.primary)
            c.drawString(MARGIN + width, top + 8, tail)

    # --------------------------------------------------------------- parties

    def _parties(self, c: canvas.Canvas, y: float) -> float:
        col2 = PAGE_W / 2 + 10

        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(self.primary)
        c.drawString(MARGIN, y, "ÉMETTEUR")
        c.drawString(col2, y, "FACTURÉ À")
        y -= 14

        left = [self.company.get("legal_name") or "Agence"]
        left += self._wrap(self.company.get("address", ""))
        left += [
            self.company.get("phone", ""),
            self.company.get("email", ""),
            self.company.get("website", ""),
        ]

        right = [self.invoice.client_name]
        right += self._wrap(self.invoice.client_address or "")
        if self.invoice.client_email:
            right.append(self.invoice.client_email)

        start = y
        for index, line in enumerate([v for v in left if v]):
            c.setFont("Helvetica-Bold" if index == 0 else "Helvetica", 9)
            c.setFillColor(self.ink if index == 0 else MUTED)
            c.drawString(MARGIN, y, line)
            y -= 12

        y_right = start
        for index, line in enumerate([v for v in right if v]):
            c.setFont("Helvetica-Bold" if index == 0 else "Helvetica", 9)
            c.setFillColor(self.ink if index == 0 else MUTED)
            c.drawString(col2, y_right, line)
            y_right -= 12

        return min(y, y_right) - 18

    @staticmethod
    def _wrap(text: str, width: int = 42) -> list[str]:
        """Découpe une adresse multi-lignes en respectant les retours saisis."""
        out: list[str] = []
        for raw in (text or "").splitlines():
            raw = raw.strip()
            while len(raw) > width:
                cut = raw.rfind(" ", 0, width)
                cut = cut if cut > 0 else width
                out.append(raw[:cut])
                raw = raw[cut:].strip()
            if raw:
                out.append(raw)
        return out

    # ---------------------------------------------------------------- lignes

    def _lines_table(self, c: canvas.Canvas, y: float) -> float:
        symbol = self.invoice.currency.symbol
        x_desc = MARGIN + 10
        # Bords droits des colonnes chiffrées, espacés pour des montants à 5 chiffres.
        x_qty = PAGE_W - MARGIN - 190
        x_price = PAGE_W - MARGIN - 105
        x_total = PAGE_W - MARGIN - 10

        # En-tête du tableau
        c.setFillColor(self.primary)
        c.rect(MARGIN, y - 6, PAGE_W - 2 * MARGIN, 22, stroke=0, fill=1)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(Color(1, 1, 1))
        c.drawString(x_desc, y + 1, "DESCRIPTION")
        c.drawRightString(x_qty, y + 1, "QTÉ")
        c.drawRightString(x_price, y + 1, "PRIX UNITAIRE")
        c.drawRightString(x_total, y + 1, "MONTANT")
        y -= 12

        for index, line in enumerate(self.invoice.lines):
            wrapped = self._wrap(line.description, width=54) or [""]
            height = 10 + 12 * len(wrapped)

            if index % 2 == 1:
                c.setFillColor(self.soft)
                c.rect(MARGIN, y - height + 12, PAGE_W - 2 * MARGIN, height, stroke=0, fill=1)

            c.setFillColor(self.ink)
            text_y = y
            for part_index, part in enumerate(wrapped):
                c.setFont("Helvetica", 9)
                c.drawString(x_desc, text_y, part)
                if part_index == 0:
                    quantity = f"{line.quantity.normalize():f}".rstrip(".")
                    c.drawRightString(x_qty, text_y, quantity)
                    c.drawRightString(x_price, text_y, _fmt(line.unit_price, symbol))
                    c.setFont("Helvetica-Bold", 9)
                    c.drawRightString(x_total, text_y, _fmt(line.total, symbol))
                text_y -= 12

            y -= height
            c.setStrokeColor(HAIRLINE)
            c.setLineWidth(0.5)
            c.line(MARGIN, y + 10, PAGE_W - MARGIN, y + 10)

        return y - 12

    # ---------------------------------------------------------------- totaux

    def _totals(self, c: canvas.Canvas, y: float) -> float:
        symbol = self.invoice.currency.symbol
        label_x = PAGE_W - MARGIN - 150
        value_x = PAGE_W - MARGIN - 10

        rows: list[tuple[str, Decimal]] = [("Sous-total", self.totals.subtotal)]
        if self.invoice.discount:
            rows.insert(0, ("Remise", -self.invoice.discount))
        rows += self.totals.taxes

        c.setFont("Helvetica", 9)
        for label, amount in rows:
            c.setFillColor(MUTED)
            c.drawString(label_x, y, label)
            c.setFillColor(self.ink)
            c.drawRightString(value_x, y, _fmt(amount, symbol))
            y -= 15

        # Bandeau du total, en magenta
        y -= 4
        c.setFillColor(self.primary)
        c.rect(label_x - 14, y - 8, PAGE_W - MARGIN - (label_x - 14), 26, stroke=0, fill=1)
        c.setFillColor(Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(label_x, y, f"TOTAL {self.invoice.currency.value}")
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(value_x, y - 1, _fmt(self.totals.total, symbol))

        return y - 40

    # ----------------------------------------------------------------- notes

    def _notes(self, c: canvas.Canvas, y: float) -> None:
        blocks: list[tuple[str, str]] = []
        if self.invoice.notes:
            blocks.append(("NOTES", self.invoice.notes))
        if self.company.get("payment_terms"):
            blocks.append(("CONDITIONS DE PAIEMENT", self.company["payment_terms"]))
        if self.company.get("payment_details"):
            blocks.append(("COORDONNÉES DE PAIEMENT", self.company["payment_details"]))

        for title, body in blocks:
            if y < 130:
                return
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(self.primary)
            c.drawString(MARGIN, y, title)
            y -= 12
            c.setFont("Helvetica", 8.5)
            c.setFillColor(MUTED)
            for part in self._wrap(body, width=95):
                c.drawString(MARGIN, y, part)
                y -= 11
            y -= 8

    # ---------------------------------------------------------------- footer

    def _footer(self, c: canvas.Canvas) -> None:
        c.setStrokeColor(HAIRLINE)
        c.setLineWidth(0.5)
        c.line(MARGIN, 74, PAGE_W - MARGIN, 74)

        legal = " · ".join(
            part
            for part in [
                f"{self.company.get('tax_number_1_label', '')} {self.company.get('tax_number_1', '')}".strip(),
                f"{self.company.get('tax_number_2_label', '')} {self.company.get('tax_number_2', '')}".strip(),
                f"No entreprise {self.company.get('registration_number', '')}".strip(),
            ]
            if part
        )

        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawString(MARGIN, 60, legal)
        c.drawString(
            MARGIN,
            48,
            f"{self.company.get('legal_name', '')} · {self.company.get('email', '')} "
            f"· {self.company.get('phone', '')} · {self.company.get('website', '')}",
        )

        c.setFillColor(self.primary)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(PAGE_W - MARGIN, 48, self.company.get("tagline", ""))

    def _signature(self, c: canvas.Canvas, signature_bytes: bytes | None) -> None:
        if not signature_bytes:
            return
        block_left = PAGE_W - MARGIN - 175
        baseline = 102
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(self.primary)
        c.drawString(block_left, baseline + 64, "SIGNATURE")
        try:
            image = ImageReader(io.BytesIO(signature_bytes))
            iw, ih = image.getSize()
            max_w, max_h = 160, 50
            ratio = min(max_w / iw, max_h / ih)
            width, height = iw * ratio, ih * ratio
            c.drawImage(
                image,
                PAGE_W - MARGIN - width,
                baseline + 8,
                width=width,
                height=height,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception:
            return
        c.setStrokeColor(self.ink)
        c.setLineWidth(0.6)
        c.line(block_left, baseline + 4, PAGE_W - MARGIN, baseline + 4)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawRightString(PAGE_W - MARGIN, baseline - 7, "Signature autorisée")


def render_invoice_pdf(
    invoice: Invoice,
    totals: InvoiceTotals,
    company: dict,
    logo_bytes: bytes | None = None,
    signature_bytes: bytes | None = None,
) -> bytes:
    return InvoiceRenderer(invoice, totals, company).render(logo_bytes, signature_bytes)
