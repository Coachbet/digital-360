"""Conversion d'un PowerPoint en PDF pour l'aperçu intégré au navigateur."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from adgi360.infrastructure.config.settings import settings


def _binary() -> str | None:
    configured = getattr(settings, "libreoffice_binary", None)
    if configured and (Path(configured).exists() or shutil.which(configured)):
        return configured
    for candidate in (
        "soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/opt/homebrew/bin/soffice",
        "/usr/local/bin/soffice",
    ):
        resolved = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if resolved:
            return resolved
    return None


def render_pptx_preview_pdf(content: bytes) -> bytes | None:
    binary = _binary()
    if not binary:
        return None
    with tempfile.TemporaryDirectory(prefix="adgi360-preview-") as raw:
        folder = Path(raw)
        source = folder / "rapport.pptx"
        source.write_bytes(content)
        env = {**os.environ, "HOME": str(folder / "lo-profile")}
        result = subprocess.run(
            [binary, "--headless", "--convert-to", "pdf", "--outdir", str(folder), str(source)],
            env=env,
            capture_output=True,
            timeout=90,
            check=False,
        )
        output = folder / "rapport.pdf"
        if result.returncode != 0 or not output.exists():
            return None
        return output.read_bytes()
