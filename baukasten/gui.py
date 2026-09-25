"""Die grafische Oberfläche (Tkinter, keine Fremdbibliotheken): Schritt für Schritt zum eigenen Linux."""
from __future__ import annotations

import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, VERSION, backends, catalog, generator
from .model import Recipe, RecipeError, split_words

LOCALES = [("de_DE.UTF-8", "Deutsch (Deutschland)"), ("de_AT.UTF-8", "Deutsch (Österreich)"), ("de_CH.UTF-8", "Deutsch (Schweiz)"),
           ("en_US.UTF-8", "English (US)"), ("en_GB.UTF-8", "English (UK)"), ("fr_FR.UTF-8", "Français"), ("es_ES.UTF-8", "Español"),
           ("it_IT.UTF-8", "Italiano"), ("pt_BR.UTF-8", "Português (Brasil)"), ("nl_NL.UTF-8", "Nederlands"),
           ("pl_PL.UTF-8", "Polski"), ("ru_RU.UTF-8", "Русский"), ("tr_TR.UTF-8", "Türkçe")]
KEYBOARDS = ["de", "us", "gb", "fr", "es", "it", "pt", "br", "nl", "pl", "ru", "tr", "ch"]
TIMEZONES = ["Europe/Berlin", "Europe/Vienna", "Europe/Zurich", "Europe/London", "Europe/Paris", "Europe/Madrid", "Europe/Rome",
             "America/New_York", "America/Chicago", "America/Los_Angeles", "America/Sao_Paulo", "Asia/Tokyo", "Asia/Shanghai", "UTC"]
STEPS = ["1  Start", "2  Desktop", "3  Bausteine", "4  Extras", "5  Bauen"]


def default_out_root() -> Path:
    docs = Path.home() / "Documents"
    return (docs if docs.is_dir() else Path.home()) / "Linux-Baukasten"


class ScrollFrame(ttk.Frame):
    """Ein Bereich, der bei Bedarf scrollt (Mausrad funktioniert, solange der Zeiger darüber steht)."""

    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._resize)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.on_width = None

    def _resize(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        if self.on_width:
            self.on_width(event.width)

    def _wheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("980x720")
        self.minsize(820, 600)
        self._loading = False
        self.recipe_path: Path | None = None
        self.cancel = threading.Event()
        self.q: queue.Queue = queue.Queue()
        self.building = False
        self.backends = backends.detect_backends()

        self._style()
        self._vars()
        self._menu()
        self._layout()
        self.load_preset("tails-like")
        self.status.configure(text=self.status.cget("text"))
        self.after(150, self._poll)

    # ------------------------------------------------------------------ Aufbau
    def _style(self):
        st = ttk.Style(self)
        if "vista" in st.theme_names() and os.name == "nt":
            st.theme_use("vista")
        elif "clam" in st.theme_names():
            st.theme_use("clam")
        st.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        st.configure("Sub.TLabel", foreground="#555555")
        st.configure("Cat.TLabel", font=("Segoe UI", 11, "bold"))
        st.configure("Desc.TLabel", foreground="#444444")
        st.configure("Err.TLabel", foreground="#b00020")
        st.configure("Note.TLabel", foreground="#8a5a00")

    def _vars(self):
        self.v_name = tk.StringVar()
        self.v_suite = tk.StringVar()
        self.v_locale = tk.StringVar()
        self.v_keyboard = tk.StringVar()
        self.v_timezone = tk.StringVar()
        self.v_hostname = tk.StringVar()
        self.v_username = tk.StringVar()
        self.v_desktop = tk.StringVar()
        self.v_boot = tk.StringVar()
        self.v_preset = tk.StringVar()
        self.v_search = tk.StringVar()
        self.v_backend = tk.StringVar()
        self.v_outdir = tk.StringVar(value=str(default_out_root()))
        self.v_feat = {f.id: tk.BooleanVar(value=False) for f in catalog.FEATURES_LIST}
        for v in (self.v_name, self.v_suite, self.v_locale, self.v_keyboard, self.v_timezone, self.v_hostname, self.v_username,
                  self.v_desktop, self.v_boot):
            v.trace_add("write", lambda *_: self._changed())
        for fid, v in self.v_feat.items():
            v.trace_add("write", lambda *_a, fid=fid: self._feature_changed(fid))
        self.v_search.trace_add("write", lambda *_: self._filter_features())

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=False)
        f.add_command(label="Neu (Vorlage „Wegwerf-System“)", command=self.new_recipe)
        f.add_command(label="Rezept laden …", accelerator="Strg+O", command=self.load_recipe)
        f.add_command(label="Rezept speichern …", accelerator="Strg+S", command=self.save_recipe)
        f.add_separator()
        f.add_command(label="Beenden", command=self.on_close)
        m.add_cascade(label="Datei", menu=f)
        p = tk.Menu(m, tearoff=False)
        for pr in catalog.PRESETS_LIST:
            p.add_command(label=pr.title, command=lambda pid=pr.id: self.load_preset(pid))
        m.add_cascade(label="Vorlagen", menu=p)
        h = tk.Menu(m, tearoff=False)
        h.add_command(label="Über Linux-Baukasten", command=self.about)
        m.add_cascade(label="Hilfe", menu=h)
        self.config(menu=m)
        self.bind_all("<Control-s>", lambda e: self.save_recipe())
        self.bind_all("<Control-o>", lambda e: self.load_recipe())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _layout(self):
        head = ttk.Frame(self, padding=(16, 10, 16, 4))
        head.pack(fill="x")
        ttk.Label(head, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(head, text=f"  Version {VERSION} (Alpha) – baue dir dein eigenes Linux", style="Sub.TLabel").pack(side="left", pady=(8, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=6)
        self.tabs = []
        for title, builder in zip(STEPS, (self._tab_start, self._tab_desktop, self._tab_features, self._tab_extras, self._tab_build)):
            page = ttk.Frame(self.nb, padding=14)
            self.nb.add(page, text=title)
            builder(page)
            self.tabs.append(page)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._changed())

        bar = ttk.Frame(self, padding=(14, 4, 14, 10))
        bar.pack(fill="x")
        self.status = ttk.Label(bar, text="", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="◀ Zurück", command=lambda: self.step(-1)).pack(side="left", padx=4)
        ttk.Button(bar, text="Weiter ▶", command=lambda: self.step(1)).pack(side="left")

    # ---- Tab 1: Start
    def _tab_start(self, page):
        page.columnconfigure(1, weight=1)
        r = 0
        ttk.Label(page, text="Womit möchtest du anfangen?", style="Cat.TLabel").grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1
        ttk.Label(page, text="Eine Vorlage stellt Desktop und Bausteine passend ein. Danach kannst du alles ändern.",
                  style="Desc.TLabel").grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 6))
        r += 1
        ttk.Label(page, text="Vorlage:").grid(row=r, column=0, sticky="w", pady=3)
        self.cb_preset = ttk.Combobox(page, textvariable=self.v_preset, state="readonly",
                                      values=[p.title for p in catalog.PRESETS_LIST])
        self.cb_preset.grid(row=r, column=1, sticky="ew", padx=6)
        ttk.Button(page, text="Vorlage übernehmen", command=self._preset_from_combo).grid(row=r, column=2)
        r += 1
        self.lbl_preset = ttk.Label(page, text="", style="Desc.TLabel", wraplength=780, justify="left")
        self.lbl_preset.grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self.cb_preset.bind("<<ComboboxSelected>>", lambda e: self._show_preset_desc())
        r += 1
        ttk.Separator(page).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6)
        r += 1
        rows = [("Name des Systems:", ttk.Entry(page, textvariable=self.v_name), "z. B. Mein-Linux (Buchstaben, Ziffern, Minus)"),
                ("Basis:", ttk.Combobox(page, textvariable=self.v_suite, state="readonly",
                                        values=list(catalog.BASES["debian"]["suites"].values())),
                 "Heute: Debian. Weitere Basen (Ubuntu, Arch ...) folgen."),
                ("Sprache:", ttk.Combobox(page, textvariable=self.v_locale, values=[f"{c}  –  {n}" for c, n in LOCALES]),
                 "Sprache und Format des fertigen Systems"),
                ("Tastatur:", ttk.Combobox(page, textvariable=self.v_keyboard, values=KEYBOARDS), "z. B. de, us, ch"),
                ("Zeitzone:", ttk.Combobox(page, textvariable=self.v_timezone, values=TIMEZONES), ""),
                ("Rechnername:", ttk.Entry(page, textvariable=self.v_hostname), "so meldet sich das System im Netzwerk"),
                ("Benutzername:", ttk.Entry(page, textvariable=self.v_username), "Live-Passwort ist \"live\" (bitte nach dem Start ändern)")]
        for label, widget, hint in rows:
            ttk.Label(page, text=label).grid(row=r, column=0, sticky="w", pady=3)
            widget.grid(row=r, column=1, sticky="ew", padx=6)
            ttk.Label(page, text=hint, style="Desc.TLabel").grid(row=r, column=2, sticky="w")
            r += 1
        self.cb_suite = rows[1][1]

    # ---- Tab 2: Desktop
    def _tab_desktop(self, page):
        ttk.Label(page, text="Wie soll die Oberfläche aussehen?", style="Cat.TLabel").pack(anchor="w")
        ttk.Label(page, text="Größenangaben sind grobe Schätzungen für die fertige ISO.", style="Desc.TLabel").pack(anchor="w", pady=(0, 8))
        for did, d in catalog.DESKTOPS.items():
            row = ttk.Frame(page)
            row.pack(fill="x", pady=3)
            ttk.Radiobutton(row, text=f"{d['title']}   (ca. +{d['size_mb'] / 1024:.1f} GB)", value=did,
                            variable=self.v_desktop).pack(anchor="w")
            ttk.Label(row, text=d["desc"], style="Desc.TLabel", wraplength=800, justify="left").pack(anchor="w", padx=24)

    # ---- Tab 3: Bausteine
    def _tab_features(self, page):
        top = ttk.Frame(page)
        top.pack(fill="x")
        ttk.Label(top, text="Was soll dein System können?", style="Cat.TLabel").pack(side="left")
        ttk.Entry(top, textvariable=self.v_search, width=28).pack(side="right")
        ttk.Label(top, text="Suchen:").pack(side="right", padx=6)
        self.sf = ScrollFrame(page)
        self.sf.pack(fill="both", expand=True, pady=(8, 0))
        self.feature_rows = []          # (Frame, Suchtext, Kategorie)
        self.cat_headers = {}
        self.desc_labels = []
        for cid, ctitle in catalog.CATEGORIES:
            hdr = ttk.Label(self.sf.inner, text=ctitle, style="Cat.TLabel")
            self.cat_headers[cid] = hdr
            for f in [x for x in catalog.FEATURES_LIST if x.category == cid]:
                row = ttk.Frame(self.sf.inner)
                ttk.Checkbutton(row, text=f"{f.title}   (ca. {f.size_mb} MB)" if f.size_mb >= 20 else f.title,
                                variable=self.v_feat[f.id]).pack(anchor="w")
                lbl = ttk.Label(row, text=f.desc, style="Desc.TLabel", wraplength=760, justify="left")
                lbl.pack(anchor="w", padx=24)
                self.desc_labels.append(lbl)
                extra = []
                if f.needs_desktop:
                    extra.append("braucht einen Desktop")
                if f.needs_non_free:
                    extra.append("nutzt Paketbereiche contrib/non-free")
                if f.note:
                    extra.append(f.note)
                if extra:
                    n = ttk.Label(row, text="ⓘ " + " · ".join(extra), style="Note.TLabel", wraplength=760, justify="left")
                    n.pack(anchor="w", padx=24)
                    self.desc_labels.append(n)
                text = " ".join((f.id, f.title, f.desc, " ".join(f.packages))).lower()
                self.feature_rows.append((row, text, cid))
        self.sf.on_width = lambda w: [lb.configure(wraplength=max(300, w - 70)) for lb in self.desc_labels]
        self._filter_features()

    def _filter_features(self):
        q = self.v_search.get().strip().lower()
        for w in self.sf.inner.winfo_children():
            w.pack_forget()
        shown = set()
        for cid, _ in catalog.CATEGORIES:
            rows = [row for row, text, c in self.feature_rows if c == cid and (not q or q in text)]
            if rows:
                self.cat_headers[cid].pack(anchor="w", pady=(12, 2))
                for row in rows:
                    row.pack(fill="x", pady=2)
                shown.add(cid)

    # ---- Tab 4: Extras
    def _tab_extras(self, page):
        ttk.Label(page, text="Eigene Wünsche", style="Cat.TLabel").pack(anchor="w")
        ttk.Label(page, text="Zusätzliche Debian-Pakete (Namen mit Leerzeichen oder Komma trennen, z. B. htop, vlc, gimp):",
                  style="Desc.TLabel").pack(anchor="w", pady=(8, 2))
        self.txt_pk = tk.Text(page, height=6, wrap="word")
        self.txt_pk.pack(fill="x")
        self.txt_pk.bind("<KeyRelease>", lambda e: self._changed())
        ttk.Label(page, text="Zusätzliche Kernel-Parameter (Fortgeschrittene, z. B. nomodeset):", style="Desc.TLabel").pack(anchor="w", pady=(12, 2))
        ttk.Entry(page, textvariable=self.v_boot).pack(fill="x")
        ttk.Label(page, text="Tipp: Paketnamen findest du auf packages.debian.org. Nicht existierende Namen lassen den Bau scheitern.",
                  style="Desc.TLabel").pack(anchor="w", pady=(12, 0))

    # ---- Tab 5: Bauen
    def _tab_build(self, page):
        ttk.Label(page, text="Zusammenfassung", style="Cat.TLabel").pack(anchor="w")
        self.txt_sum = tk.Text(page, height=11, wrap="word", state="disabled", background="#f7f7f7")
        self.txt_sum.pack(fill="x", pady=(4, 8))
        grid = ttk.Frame(page)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        ttk.Label(grid, text="Wo bauen:").grid(row=0, column=0, sticky="w", pady=2)
        self.cb_backend = ttk.Combobox(grid, textvariable=self.v_backend, state="readonly",
                                       values=[b.label + ("" if b.available else "  (nicht verfügbar)") for b in self.backends])
        self.cb_backend.grid(row=0, column=1, sticky="ew", padx=6)
        self.cb_backend.bind("<<ComboboxSelected>>", lambda e: self._backend_hint())
        self.lbl_hint = ttk.Label(grid, text="", style="Note.TLabel", wraplength=780, justify="left")
        self.lbl_hint.grid(row=1, column=0, columnspan=3, sticky="w")
        ttk.Label(grid, text="Ausgabeordner:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(grid, textvariable=self.v_outdir).grid(row=2, column=1, sticky="ew", padx=6)
        ttk.Button(grid, text="Wählen …", command=self.choose_outdir).grid(row=2, column=2)
        btns = ttk.Frame(page)
        btns.pack(fill="x", pady=8)
        self.btn_export = ttk.Button(btns, text="Projekt exportieren", command=self.export_project)
        self.btn_export.pack(side="left")
        self.btn_build = ttk.Button(btns, text="ISO bauen", command=self.build_iso)
        self.btn_build.pack(side="left", padx=8)
        self.btn_cancel = ttk.Button(btns, text="Abbrechen", command=self.cancel_build, state="disabled")
        self.btn_cancel.pack(side="left")
        self.progress = ttk.Progressbar(btns, mode="determinate", length=160, maximum=100)
        self.progress.pack(side="right")
        frame = ttk.Frame(page)
        frame.pack(fill="both", expand=True)
        self.txt_log = tk.Text(frame, height=8, wrap="none", state="disabled", background="#101418", foreground="#d8dee9")
        sb = ttk.Scrollbar(frame, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=sb.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # erste verfügbare Möglichkeit vorwählen (WSL/Linux/Docker), sonst Export
        pick = next((b for b in self.backends if b.available and b.id != "export"), self.backends[-1])
        self.v_backend.set(pick.label + ("" if pick.available else "  (nicht verfügbar)"))
        self._backend_hint()

    # ------------------------------------------------------------------ Rezept <-> Oberfläche
    def _suite_id(self) -> str:
        text = self.v_suite.get()
        for sid, title in catalog.BASES["debian"]["suites"].items():
            if text == title or text == sid:
                return sid
        return text

    def read_recipe(self) -> Recipe:
        feats = [fid for fid, v in self.v_feat.items() if v.get()]
        return Recipe(name=self.v_name.get().strip(), base="debian", suite=self._suite_id(), desktop=self.v_desktop.get(),
                      features=[f.id for f in catalog.FEATURES_LIST if f.id in feats],
                      extra_packages=split_words(self.txt_pk.get("1.0", "end")) if hasattr(self, "txt_pk") else [],
                      extra_boot_params=split_words(self.v_boot.get()),
                      locale=self.v_locale.get().split()[0] if self.v_locale.get().split() else "",
                      keyboard=self.v_keyboard.get().strip(), timezone=self.v_timezone.get().strip(),
                      hostname=self.v_hostname.get().strip(), username=self.v_username.get().strip())

    def apply_recipe(self, r: Recipe):
        self._loading = True
        try:
            self.v_name.set(r.name)
            self.v_suite.set(catalog.BASES.get(r.base, catalog.BASES["debian"])["suites"].get(r.suite, r.suite))
            label = next((f"{c}  –  {n}" for c, n in LOCALES if c == r.locale), r.locale)
            self.v_locale.set(label)
            self.v_keyboard.set(r.keyboard)
            self.v_timezone.set(r.timezone)
            self.v_hostname.set(r.hostname)
            self.v_username.set(r.username)
            self.v_desktop.set(r.desktop if r.desktop in catalog.DESKTOPS else "xfce")
            self.v_boot.set(" ".join(r.extra_boot_params))
            self.txt_pk.delete("1.0", "end")
            self.txt_pk.insert("1.0", " ".join(r.extra_packages))
            for fid, v in self.v_feat.items():
                v.set(fid in r.features)
        finally:
            self._loading = False
        self._changed()

    def _feature_changed(self, fid: str):
        if self._loading:
            return
        if self.v_feat[fid].get():
            self._loading = True
            try:
                notes = []
                for other in catalog.resolve_features([fid]):
                    if other != fid and not self.v_feat[other].get():
                        self.v_feat[other].set(True)
                        notes.append(f"„{catalog.FEATURES[other].title}“ wurde dazu gewählt")
                for c in catalog.FEATURES[fid].conflicts:
                    if self.v_feat[c].get():
                        self.v_feat[c].set(False)
                        notes.append(f"„{catalog.FEATURES[c].title}“ wurde abgewählt (passt nicht zusammen)")
            finally:
                self._loading = False
            self._note = " · ".join(notes)
        else:
            self._note = ""
        self._changed()

    _note = ""

    def _changed(self):
        if self._loading or not hasattr(self, "txt_sum"):
            return
        r = self.read_recipe()
        errors = catalog.validate(r)
        self._errors = errors
        if errors:
            self.status.configure(text="⚠ " + errors[0] + (f"  (+{len(errors) - 1} weitere)" if len(errors) > 1 else ""), style="Err.TLabel")
        else:
            n = len(catalog.resolve_features(r.features))
            base = f"{n} Bausteine · {len(catalog.package_list(r))} Pakete · ISO ca. {catalog.estimate_size_mb(r) / 1024:.1f} GB (grobe Schätzung)"
            self.status.configure(text=(self._note + "   |   " if self._note else "") + base, style="TLabel")
        state = "disabled" if errors or self.building else "normal"
        for b in (self.btn_export, self.btn_build):
            b.configure(state=state)
        self._summary(r, errors)

    def _summary(self, r: Recipe, errors):
        lines = [f"Name:      {r.name}", f"Basis:     {catalog.BASES['debian']['title']} {r.suite}",
                 f"Desktop:   {catalog.DESKTOPS.get(r.desktop, {}).get('title', r.desktop)}",
                 f"Sprache:   {r.locale}   Tastatur: {r.keyboard}   Zeitzone: {r.timezone}",
                 f"Benutzer:  {r.username} (Passwort: live)   Rechner: {r.hostname}"]
        if not errors:
            feats = catalog.resolve_features(r.features)
            lines.append("Bausteine: " + (", ".join(catalog.FEATURES[i].title for i in feats) if feats else "(keine)"))
            if r.extra_packages:
                lines.append("Extra-Pakete: " + ", ".join(r.extra_packages))
            lines.append(f"Insgesamt {len(catalog.package_list(r))} Pakete · ISO ca. {catalog.estimate_size_mb(r) / 1024:.1f} GB (grob geschätzt)")
            lines.append(f"Der Bau braucht: {catalog.BUILD_NEEDS}.")
        else:
            lines.append("")
            lines += ["⚠ " + e for e in errors]
        self.txt_sum.configure(state="normal")
        self.txt_sum.delete("1.0", "end")
        self.txt_sum.insert("1.0", "\n".join(lines))
        self.txt_sum.configure(state="disabled")

    # ------------------------------------------------------------------ Aktionen
    def step(self, d):
        i = max(0, min(len(self.tabs) - 1, self.nb.index(self.nb.select()) + d))
        self.nb.select(i)

    def _show_preset_desc(self):
        p = next((x for x in catalog.PRESETS_LIST if x.title == self.v_preset.get()), None)
        self.lbl_preset.configure(text=p.desc if p else "")

    def _preset_from_combo(self):
        p = next((x for x in catalog.PRESETS_LIST if x.title == self.v_preset.get()), None)
        if p is None:
            messagebox.showinfo(APP_NAME, "Bitte zuerst eine Vorlage aus der Liste wählen.")
            return
        self.load_preset(p.id)

    def load_preset(self, pid: str):
        name = self.v_name.get().strip() or "Mein-Linux"
        r = catalog.recipe_from_preset(pid, name if not name.startswith("Mein-Linux") else name)
        self.apply_recipe(r)
        self.v_preset.set(catalog.PRESETS[pid].title)
        self._show_preset_desc()
        self.status.configure(text=f"Vorlage „{catalog.PRESETS[pid].title}“ geladen.")

    def new_recipe(self):
        self.recipe_path = None
        self.load_preset("tails-like")

    def save_recipe(self):
        r = self.read_recipe()
        path = filedialog.asksaveasfilename(defaultextension=".baukasten.json", initialfile=f"{r.name}.baukasten.json",
                                            filetypes=[("Baukasten-Rezept", "*.baukasten.json"), ("JSON", "*.json")])
        if path:
            Path(path).write_text(r.to_json(), encoding="utf-8")
            self.recipe_path = Path(path)
            self.status.configure(text=f"Rezept gespeichert: {path}")

    def load_recipe(self):
        path = filedialog.askopenfilename(filetypes=[("Baukasten-Rezept", "*.json"), ("Alle Dateien", "*.*")])
        if not path:
            return
        try:
            r = Recipe.from_json(Path(path).read_text(encoding="utf-8"))
        except (RecipeError, OSError, UnicodeDecodeError) as e:
            messagebox.showerror(APP_NAME, f"Das Rezept lässt sich nicht laden:\n{e}")
            return
        self.recipe_path = Path(path)
        self.apply_recipe(r)

    def choose_outdir(self):
        d = filedialog.askdirectory(initialdir=self.v_outdir.get() or str(Path.home()))
        if d:
            self.v_outdir.set(d)

    def _backend(self):
        label = self.v_backend.get()
        for b in self.backends:
            if label.startswith(b.label):
                return b
        return self.backends[-1]

    def _backend_hint(self):
        b = self._backend()
        self.lbl_hint.configure(text=("" if b.available else "⚠ " + b.hint) if b.id != "export" else
                                "Das Projekt wird nur erzeugt; gebaut wird später von Hand (siehe LIESMICH.txt im Ordner).")

    def _project_dir(self, r: Recipe) -> Path:
        return Path(self.v_outdir.get().strip() or default_out_root()) / r.name

    def log(self, text: str):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def export_project(self, quiet=False):
        r = self.read_recipe()
        errors = catalog.validate(r)
        if errors:
            messagebox.showerror(APP_NAME, "\n".join(errors))
            return None
        out = self._project_dir(r)
        if out.exists() and any(out.iterdir()) and not quiet:
            if not messagebox.askyesno(APP_NAME, f"Der Ordner existiert schon:\n{out}\n\nInhalt überschreiben (Projektdateien werden ersetzt)?"):
                return None
        try:
            files = generator.generate(r, out)
        except (RecipeError, OSError) as e:
            messagebox.showerror(APP_NAME, f"Export fehlgeschlagen:\n{e}")
            return None
        self.log(f"Projekt exportiert: {out}  ({len(files)} Dateien)")
        if not quiet:
            messagebox.showinfo(APP_NAME, f"Projekt exportiert:\n{out}\n\nZum Bauen: siehe LIESMICH.txt in diesem Ordner.")
        return out

    def build_iso(self):
        b = self._backend()
        if b.id == "export":
            self.export_project()
            return
        if not b.available:
            messagebox.showwarning(APP_NAME, b.hint or "Diese Möglichkeit ist hier nicht verfügbar.")
            return
        if not messagebox.askokcancel(APP_NAME, "Der Bau lädt mehrere Gigabyte aus dem Internet und dauert 20–60 Minuten. "
                                                f"Benötigt: {catalog.BUILD_NEEDS}.\n\nJetzt starten?\n\n"
                                                "Hinweis: Diese Version ist eine Alpha – der komplette ISO-Bau ist noch nicht auf allen "
                                                "Systemen geprüft. Das Projekt lässt sich auch exportieren und von Hand bauen."):
            return
        out = self.export_project(quiet=True)
        if out is None:
            return
        distro = None
        if b.id == "wsl":
            names = backends.wsl_distros()
            distro = names[0] if names else None
        try:
            cmd, cwd = backends.build_command(b.id, out, distro)
        except ValueError as e:
            messagebox.showerror(APP_NAME, str(e))
            return
        self.cancel.clear()
        self.building = True
        self.btn_cancel.configure(state="normal")
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        self._changed()
        self.log("--- Bau gestartet: " + " ".join(cmd))

        def work():
            try:
                code = backends.run_streaming(cmd, lambda s: self.q.put(("line", s)), self.cancel, cwd)
            except OSError as e:
                self.q.put(("line", f"Fehler beim Start: {e}"))
                code = 127
            self.q.put(("done", (code, out)))

        threading.Thread(target=work, daemon=True).start()

    def cancel_build(self):
        self.cancel.set()
        self.log("--- Abbruch angefordert ...")

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "line":
                    self.log(payload)
                else:
                    code, out = payload
                    self.building = False
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=0)
                    self.btn_cancel.configure(state="disabled")
                    self._changed()
                    isos = sorted(Path(out).glob("*.iso"))
                    if code == 0 and isos:
                        self.log(f"--- Fertig: {isos[0]}")
                        messagebox.showinfo(APP_NAME, f"Fertig! Die ISO liegt hier:\n{isos[0]}\n\n"
                                                      "Auf einen USB-Stick schreiben (z. B. Rufus oder balenaEtcher) und davon starten.")
                    elif code == -1:
                        self.log("--- Abgebrochen.")
                    else:
                        self.log(f"--- Bau beendet mit Code {code} (keine ISO gefunden). Siehe Protokoll oben / build.log im Projektordner.")
                        messagebox.showwarning(APP_NAME, f"Der Bau ist fehlgeschlagen (Code {code}).\nDetails im Protokoll und in build.log.")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(150, self._poll)

    def about(self):
        messagebox.showinfo(APP_NAME, f"{APP_NAME} {VERSION} (Alpha)\n\nStelle dir dein eigenes Linux aus Bausteinen zusammen "
                                      "(Live-USB, Installer, Rettungssystem ...). Basis heute: Debian, gebaut mit live-build.\n\n"
                                      "MIT-Lizenz · https://github.com/LurNyx/Linux-Baukasten\n"
                                      "Nicht mit dem Debian-Projekt verbunden.")

    def on_close(self):
        if self.building and not messagebox.askyesno(APP_NAME, "Der Bau läuft noch. Wirklich beenden (Bau wird abgebrochen)?"):
            return
        self.cancel.set()
        self.destroy()


def enable_dpi_awareness():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def main() -> int:
    enable_dpi_awareness()
    app = App()
    app.mainloop()
    return 0


def selftest(export_dir=None) -> int:
    """Baut die Oberfläche auf, wählt Vorlagen, exportiert ein Projekt und schließt wieder (für Tests und die EXE)."""
    enable_dpi_awareness()
    app = App()
    try:
        app.withdraw()
        app.update()
        for p in catalog.PRESETS_LIST:
            app.load_preset(p.id)
            app.update()
            assert not app._errors, (p.id, app._errors)
            assert set(app.read_recipe().features) == set(catalog.resolve_features(catalog.recipe_from_preset(p.id).features)), p.id
        app.load_preset("kali-like")
        app.v_feat["amnesic-full"].set(True)                    # schließt Persistenz aus (Konflikt)
        app.update()
        assert not app.v_feat["persistence"].get() and app.v_feat["amnesic-full"].get()
        app.v_feat["persistence-encrypted"].set(True)          # bringt Persistenz mit, schließt Amnesic aus
        app.update()
        assert app.v_feat["persistence"].get() and not app.v_feat["amnesic-full"].get()
        app.v_desktop.set("none")
        app.update()
        assert app._errors, "Firefox ohne Desktop muss gemeldet werden"
        app.load_preset("tails-like")
        out = Path(export_dir or tempfile.mkdtemp(prefix="baukasten-selftest-"))
        app.v_outdir.set(str(out))
        proj = app.export_project(quiet=True)
        assert proj and (proj / "auto" / "config").is_file() and (proj / "build.sh").is_file(), proj
        print(f"GUI-Selbsttest OK ({len(catalog.PRESETS_LIST)} Vorlagen, Export nach {proj})")
        return 0
    finally:
        app.destroy()


if __name__ == "__main__":
    sys.exit(main())
