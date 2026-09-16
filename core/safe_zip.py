"""Säker uppackning av zip-arkiv — skyddet mot zip-slip.

Bakgrund (hittad i domargranskningen av OmaAmp 2026-09-16): temainläsningen packade
upp arkiv med `os.path.join(dest, member_name)` och skrev post för post. Ett arkiv
med en post som `repo-main/../../../.config/autostart/x.desktop` skriver utanför
temamappen — och eftersom arkivet kan komma från ett GitHub-repo någon annan äger
är det en väg in i användarens hemkatalog, inte ett teoretiskt fel.

Regeln här är enkel: **en post får bara hamna inuti målmappen.** Allt annat nekas,
och nekandet redovisas i stället för att tigas ihjäl — den som packar upp ska kunna
säga "tre poster hoppades över" och varför.

Använd `extract_zip_safely` i stället för `ZipFile.extractall` och i stället för att
bygga sökvägar för hand. Två fällor som är värda att känna till:

* `extractall` i Python 3.6+ tar bort `..`-bitar, men den skapar också filer för
  symlink-poster och skriver dem dit arkivet pekar om man läser dem själv.
* En post som börjar med `/` eller `C:\\` är absolut, och en post med `\\` i stället
  för `/` kommer från ett arkiv byggt på Windows — båda måste hanteras.

Det här skyddet handlar om **var** filer hamnar. Skydd mot zip-bomber (ett litet
arkiv som packas upp till gigabytes) är en annan sak och ligger utanför; den dag
teman hämtas automatiskt från främmande servrar bör en storleksgräns till.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass, field

__all__ = [
    "UnsafeMemberError",
    "ExtractReport",
    "safe_member_path",
    "extract_zip_safely",
]


class UnsafeMemberError(ValueError):
    """Arkivposten pekar utanför målmappen (eller går inte att tolka)."""


@dataclass
class ExtractReport:
    """Vad som hände: det som skrevs, och det som nekades med skäl."""

    dest_root: str
    extracted: list = field(default_factory=list)
    skipped: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.skipped

    def summary(self) -> str:
        if not self.skipped:
            return f"{len(self.extracted)} filer packades upp"
        return (
            f"{len(self.extracted)} filer packades upp, "
            f"{len(self.skipped)} nekades: " + "; ".join(f"{n} ({r})" for n, r in self.skipped[:3])
        )


def safe_member_path(dest_root: str, member_name: str, strip_prefix: int = 0) -> str:
    """Sökvägen en arkivpost får skrivas till — eller `UnsafeMemberError`.

    `strip_prefix` tar bort så många ledande mappnamn (GitHub-arkiv har alltid en
    toppmapp som `repo-main/`). Den tas bort **innan** resten granskas, så att ett
    försök att gömma en traversal bakom toppmappen inte slinker igenom.
    """
    if not member_name or "\x00" in member_name:
        raise UnsafeMemberError("tomt eller trasigt postnamn")

    # Windows-arkiv använder backslash; normalisera först så att skyddet inte
    # kan kringgås genom att välja separator.
    name = member_name.replace("\\", "/")

    # Absoluta sökvägar: "/foo", "C:/foo", "C:foo", "//server/share".
    if name.startswith("/"):
        raise UnsafeMemberError("absolut sökväg")
    if len(name) >= 2 and name[1] == ":":
        raise UnsafeMemberError("sökväg med enhetsbeteckning")

    parts = [p for p in name.split("/") if p not in ("", ".")]
    if strip_prefix:
        parts = parts[strip_prefix:]

    for p in parts:
        if p == "..":
            raise UnsafeMemberError("går utanför målmappen (..)")
        if os.path.isabs(p) or (len(p) >= 2 and p[1] == ":"):
            raise UnsafeMemberError("absolut sökväg i posten")

    if not parts:
        raise UnsafeMemberError("posten pekar på målmappen själv")

    dest_real = os.path.realpath(dest_root)
    target = os.path.realpath(os.path.join(dest_real, *parts))

    # Sista kontrollen: även om delarna såg snälla ut får målet inte ligga utanför.
    if target != dest_real and not target.startswith(dest_real + os.sep):
        raise UnsafeMemberError("hamnar utanför målmappen")
    return target


def extract_zip_safely(source, dest_root: str, strip_prefix: int = 0) -> ExtractReport:
    """Packar upp `source` (en sökväg eller en öppen ZipFile) i `dest_root`.

    Varje post granskas av `safe_member_path`. Poster som nekas skrivs **inte** och
    hamnar i rapporten — ingenting försvinner i tysthet.
    """
    report = ExtractReport(dest_root=dest_root)
    os.makedirs(dest_root, exist_ok=True)

    def _run(z: zipfile.ZipFile) -> None:
        for info in z.infolist():
            name = info.filename
            is_dir = name.endswith("/") or name.endswith("\\")
            try:
                target = safe_member_path(dest_root, name, strip_prefix)
            except UnsafeMemberError as exc:
                report.skipped.append((name, str(exc)))
                continue
            if is_dir:
                os.makedirs(target, exist_ok=True)
                continue
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
            report.extracted.append(os.path.relpath(target, dest_root))

    if isinstance(source, zipfile.ZipFile):
        _run(source)
    else:
        with zipfile.ZipFile(source, "r") as z:
            _run(z)
    return report
