"""Das Rezept: alles, was man in der Oberfläche einstellt - als einfache, speicherbare Daten (JSON)."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

SCHEMA = 1

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]+$")
LOCALE_RE = re.compile(r"^[a-z]{2,3}_[A-Z]{2}\.UTF-8$")
KEYMAP_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]+)?$")
TZ_RE = re.compile(r"^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+)+)$")
BOOT_PARAM_RE = re.compile(r"^[A-Za-z0-9_.:,=/+-]+$")


class RecipeError(ValueError):
    """Das Rezept ist unvollständig oder widersprüchlich."""


@dataclass
class Recipe:
    name: str = "Mein-Linux"
    base: str = "debian"
    suite: str = "trixie"
    desktop: str = "xfce-lean"
    features: list = field(default_factory=list)
    extra_packages: list = field(default_factory=list)
    extra_boot_params: list = field(default_factory=list)
    locale: str = "de_DE.UTF-8"
    keyboard: str = "de"
    timezone: str = "Europe/Berlin"
    hostname: str = "baukasten"
    username: str = "user"
    boot_timeout: int = 10        # Sekunden bis zum automatischen Start im Bootmenü; 0 = auf Eingabe warten
    schema: int = SCHEMA

    # ---- Speichern / Laden
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "Recipe":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise RecipeError(f"Das ist keine gültige Rezept-Datei: {e}") from e
        if not isinstance(data, dict):
            raise RecipeError("Das ist keine gültige Rezept-Datei (Objekt erwartet).")
        if data.get("schema", SCHEMA) > SCHEMA:
            raise RecipeError("Dieses Rezept stammt aus einer neueren Programmversion.")
        known = {f for f in cls.__dataclass_fields__}
        r = cls(**{k: v for k, v in data.items() if k in known})
        for lst in ("features", "extra_packages", "extra_boot_params"):
            v = getattr(r, lst)
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise RecipeError(f"'{lst}' muss eine Liste von Wörtern sein.")
        return r

    def copy(self) -> "Recipe":
        return Recipe.from_json(self.to_json())


def split_words(text: str) -> list:
    """'a b, c\\nd' -> ['a', 'b', 'c', 'd'] (Reihenfolge bleibt, doppelte fallen weg)."""
    out = []
    for w in re.split(r"[\s,;]+", text.strip()):
        if w and w not in out:
            out.append(w)
    return out


def check_fields(r: Recipe) -> list:
    """Formale Prüfung der Felder (ohne Katalog). -> Liste von Fehlertexten (leer = ok)."""
    errors = []
    if not NAME_RE.match(r.name):
        errors.append("Name: nur Buchstaben, Ziffern, Punkt, Minus, Unterstrich (max. 40 Zeichen, beginnt mit Buchstabe/Ziffer).")
    if not HOST_RE.match(r.hostname):
        errors.append("Rechnername: nur a-z, 0-9 und Minus (max. 32 Zeichen).")
    if not USER_RE.match(r.username):
        errors.append("Benutzername: nur a-z, 0-9, Minus, Unterstrich (beginnt mit Buchstabe).")
    if not LOCALE_RE.match(r.locale):
        errors.append("Sprache/Gebietsschema muss wie de_DE.UTF-8 aussehen.")
    if not KEYMAP_RE.match(r.keyboard):
        errors.append("Tastaturlayout muss wie de oder us aussehen.")
    if not TZ_RE.match(r.timezone):
        errors.append("Zeitzone muss wie Europe/Berlin aussehen.")
    if isinstance(r.boot_timeout, bool) or not isinstance(r.boot_timeout, int) or not 0 <= r.boot_timeout <= 300:
        errors.append("Bootmenü-Wartezeit: eine ganze Zahl von 0 bis 300 Sekunden (0 = auf Eingabe warten).")
    for p in r.extra_packages:
        if not PKG_RE.match(p):
            errors.append(f"Ungültiger Paketname: {p!r}")
    for p in r.extra_boot_params:
        if not BOOT_PARAM_RE.match(p):
            errors.append(f"Ungültiger Kernel-Parameter: {p!r}")
    return errors
