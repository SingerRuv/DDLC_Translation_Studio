"""Tkinter translation editor."""
import csv
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import APP, load_settings, save_settings
from .indexer import index_workspace
from .modinfo import find_mod_root
from .project import Project
from .build import build_translated
from .rewrite import apply_translations as apply_rewrites
from .tools import ToolConfig
from .validate import validate
from .workspace import prepare_workspace, snapshot_dir

class SettingsDialog(tk.Toplevel):
    def __init__(self, master, settings, on_save):
        super().__init__(master)
        self.title("Tool settings")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.settings = dict(settings)
        self.on_save = on_save
        self.vars = {}
        entries = (
            ("rpa_extractor", "RPA extractor"),
            ("rpyc_decompiler", "RPYC decompiler"),
            ("renpy", "Ren'Py executable"),
        )
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        for row, (key, label) in enumerate(entries):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w",
                                             pady=4)
            value = tk.StringVar(value=str(self.settings.get(key, "")))
            ttk.Entry(body, textvariable=value, width=55).grid(
                row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
            self.vars[key] = value
        ttk.Label(
            body, text="Arguments use {input} and {output}; edit settings.json "
                       "for custom arguments.",
            wraplength=480).grid(row=len(entries), column=0, columnspan=2,
                                 sticky="w", pady=(8, 4))
        actions = ttk.Frame(body)
        actions.grid(row=len(entries) + 1, column=0, columnspan=2,
                     sticky="e", pady=(8, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(
            side="left", padx=(0, 8))
        ttk.Button(actions, text="Save", command=self._save).pack(side="left")
        body.columnconfigure(1, weight=1)

    def _save(self):
        for key, variable in self.vars.items():
            self.settings[key] = variable.get().strip()
        try:
            save_settings(self.settings)
        except OSError as exc:
            messagebox.showerror(APP, "Could not save settings:\n%s" % exc,
                                 parent=self)
            return
        self.on_save(self.settings)
        self.destroy()


def _prepare_project(mod, project_dir, settings):
    project = Project(project_dir)
    try:
        root = find_mod_root(mod)
        project.set_meta("source", mod)
        project.set_meta("mod_root", root)
        project.set_meta("app", APP)
        workspace = prepare_workspace(
            mod, project_dir, tools=ToolConfig(settings))
        snapshot = snapshot_dir(project_dir)
        project.set_meta("workspace", workspace)
        project.set_meta("snapshot", snapshot)
        stats = index_workspace(project, workspace, snapshot)
        return str(project_dir), stats
    finally:
        project.close()


def _index_project(project_path):
    project = Project(project_path)
    try:
        workspace = project.get_meta("workspace")
        snapshot = project.get_meta("snapshot") or workspace
        return index_workspace(project, workspace, snapshot)
    finally:
        project.close()


def _apply_project(project_path, workspace):
    project = Project(project_path)
    try:
        return apply_rewrites(project, workspace)
    finally:
        project.close()


def _build_project(project_path, workspace, output, settings):
    project = Project(project_path)
    try:
        return build_translated(
            project, workspace, output, tools=ToolConfig(settings))
    finally:
        project.close()



class TranslationApp(tk.Tk):
    def __init__(self, project_path=None):
        super().__init__()
        self.title(APP)
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.settings = load_settings()
        self.project = None
        self.workspace = None
        self.rows = []
        self.current_id = None
        self.search_var = tk.StringVar()
        self.status_filter = tk.StringVar(value="All")
        self.project_label = tk.StringVar(value="No project open")
        self.status = tk.StringVar(value="Open or create a project.")
        self.context_var = tk.StringVar()
        self.validation_var = tk.StringVar()
        self._jobs = queue.Queue()
        self._worker = None
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Control-s>", lambda _event: self._save_current())
        self.after(100, self._poll_jobs)
        if project_path:
            self.open_project(project_path)

    def _build_ui(self):
        header = tk.Frame(self, bg="#1b2026", height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=APP, bg="#1b2026", fg="#ffffff",
                 font=("Segoe UI", 14, "bold")).pack(
            side="left", padx=14, pady=10)
        tk.Label(header, textvariable=self.project_label, bg="#1b2026",
                 fg="#b9c2cc", font=("Segoe UI", 9)).pack(
            side="left", padx=(4, 0), pady=12)

        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill="x")
        for text, command in (
                ("New project...", self.new_project),
                ("Open project...", self.open_project_dialog),
                ("Index", self.index_project),
                ("Apply translations", self.apply_translations),
                ("Build translated mod", self.build_project),
                ("Validate", self.validate_project),
                ("Export CSV", self.export_csv),
                ("Import CSV", self.import_csv),
                ("Settings...", self.show_settings)):
            ttk.Button(toolbar, text=text, command=command).pack(
                side="left", padx=(0, 6))

        filters = ttk.Frame(self, padding=(10, 0))
        filters.pack(fill="x")
        ttk.Label(filters, text="Search:").pack(side="left")
        ttk.Entry(filters, textvariable=self.search_var, width=28).pack(
            side="left", padx=(4, 12))
        self.search_var.trace_add("write", lambda *_: self._refresh_table())
        ttk.Label(filters, text="Status:").pack(side="left")
        ttk.Combobox(filters, textvariable=self.status_filter, state="readonly",
                     width=12, values=("All", "pending", "translated")).pack(
            side="left", padx=(4, 0))
        self.status_filter.trace_add("write",
                                     lambda *_: self._refresh_table())

        ttk.Label(self, textvariable=self.status, padding=(10, 4)).pack(
            fill="x")

        body = ttk.Panedwindow(self, orient="vertical")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        table_frame = ttk.Frame(body)
        columns = ("id", "file", "line", "status", "original", "translation")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="browse")
        for column, label, width in (
                ("id", "ID", 50), ("file", "File", 240), ("line", "Line", 55),
                ("status", "Status", 90), ("original", "Original", 320),
                ("translation", "Translation", 320)):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        body.add(table_frame, weight=3)

        detail = ttk.LabelFrame(body, text="Translation", padding=10)
        body.add(detail, weight=2)
        ttk.Label(detail, text="Original").pack(anchor="w")
        self.original_text = tk.Text(detail, height=3, wrap="word",
                                     state="disabled")
        self.original_text.pack(fill="x", pady=(2, 8))
        ttk.Label(detail, text="Translation").pack(anchor="w")
        self.translation_text = tk.Text(detail, height=4, wrap="word")
        self.translation_text.pack(fill="both", expand=True, pady=(2, 6))
        ttk.Label(detail, textvariable=self.context_var).pack(anchor="w")
        ttk.Label(detail, textvariable=self.validation_var,
                  foreground="#b00020").pack(anchor="w")
        actions = ttk.Frame(detail)
        actions.pack(fill="x", pady=(6, 0))
        ttk.Button(actions, text="Save translation",
                   command=self._save_current).pack(side="right")
        ttk.Label(actions, text="Ctrl+S").pack(side="right", padx=(0, 8))


    def _start_job(self, message, job, done):
        if self._worker is not None and self._worker.is_alive():
            messagebox.showinfo(APP, "An operation is already running.")
            return
        self.status.set(message)
        self._worker = threading.Thread(
            target=self._worker_run, args=(job, done), daemon=True)
        self._worker.start()

    def _worker_run(self, job, done):
        try:
            result = job()
        except Exception as exc:
            self._jobs.put(("error", str(exc)))
        else:
            self._jobs.put(("done", (result, done)))

    def _poll_jobs(self):
        try:
            kind, payload = self._jobs.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_jobs)
            return
        self._worker = None
        if kind == "error":
            self.status.set("Operation failed.")
            messagebox.showerror(APP, payload)
        else:
            result, done = payload
            try:
                done(result)
            except Exception as exc:
                self.status.set("Operation failed.")
                messagebox.showerror(APP, str(exc))
        self.after(100, self._poll_jobs)


    def _set_project(self, project, workspace=None):
        if self.project is not None:
            self.project.close()
        self.project = project
        self.workspace = workspace or project.get_meta("workspace")
        self.project_label.set(str(project.path))
        self.title("%s - %s" % (APP, project.path.name))
        self._reload_rows()

    def _reload_rows(self):
        self.rows = list(self.project.strings()) if self.project else []
        self._refresh_table()
        self.status.set("%d strings." % len(self.rows))

    def _refresh_table(self):
        if not hasattr(self, "tree"):
            return
        query = self.search_var.get().strip().casefold()
        wanted = self.status_filter.get()
        for item in self.tree.get_children():
            self.tree.delete(item)
        shown = 0
        for row in self.rows:
            if wanted != "All" and row["status"] != wanted:
                continue
            haystack = " ".join((
                row["relative_path"], row["original"], row["translation"],
                row["context"])).casefold()
            if query and query not in haystack:
                continue
            self.tree.insert("", "end", iid=str(row["id"]), values=(
                row["id"], row["relative_path"], row["line"], row["status"],
                row["original"], row["translation"]))
            shown += 1
        if self.rows:
            self.status.set("%d of %d strings." % (shown, len(self.rows)))

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection or self.project is None:
            return
        row = self.project.get_string(int(selection[0]))
        if row is None:
            return
        self.current_id = row["id"]
        self.original_text.configure(state="normal")
        self.original_text.delete("1.0", "end")
        self.original_text.insert("1.0", row["original"])
        self.original_text.configure(state="disabled")
        self.translation_text.delete("1.0", "end")
        self.translation_text.insert("1.0", row["translation"])
        self.context_var.set("Context: %s | %s:%s" % (
            row["context"] or "-", row["relative_path"], row["line"]))
        problems = validate(row["original"], row["translation"])
        self.validation_var.set("; ".join(problems) if problems else "")

    def _save_current(self):
        if self.project is None or self.current_id is None:
            return
        row = self.project.get_string(self.current_id)
        if row is None:
            return
        translation = self.translation_text.get("1.0", "end-1c")
        problems = validate(row["original"], translation)
        if problems and not messagebox.askyesno(
                APP, "Validation warnings:\n%s\n\nSave anyway?" %
                     "\n".join(problems)):
            return
        self.project.set_translation(self.current_id, translation)
        self._reload_rows()
        self.tree.selection_set(str(self.current_id))
        self.tree.see(str(self.current_id))
        self.status.set("Translation saved.")

    def new_project(self):
        mod = filedialog.askdirectory(title="Select precompiled mod")
        if not mod:
            return
        project_dir = filedialog.askdirectory(
            title="Select project folder (empty recommended)")
        if not project_dir:
            return

        def work():
            return _prepare_project(mod, project_dir, dict(self.settings))

        def done(result):
            path, stats = result
            self.open_project(path)
            self.status.set("Indexed %d strings from %d files." % (
                stats["strings"], stats["files"]))

        self._start_job("Preparing workspace...", work, done)

    def open_project(self, path):
        path = Path(path)
        if not (path / "project.sqlite3").is_file():
            messagebox.showerror(APP, "Not a translation project:\n%s" % path)
            return
        try:
            project = Project(path)
            self._set_project(project)
        except Exception as exc:
            messagebox.showerror(APP, "Could not open project:\n%s" % exc)

    def open_project_dialog(self):
        path = filedialog.askdirectory(title="Open translation project")
        if path:
            self.open_project(path)

    def index_project(self):
        if self.project is None:
            return
        workspace = self.project.get_meta("workspace")
        if not workspace or not Path(workspace).is_dir():
            messagebox.showwarning(APP, "This project has no workspace.")
            return
        project_path = str(self.project.path)

        def done(stats):
            self._reload_rows()
            self.status.set("Indexed %d strings from %d files." % (
                stats["strings"], stats["files"]))

        self._start_job("Indexing...", lambda: _index_project(project_path),
                        done)

    def apply_translations(self):
        if self.project is None:
            return
        workspace = self.project.get_meta("workspace")
        if not workspace or not Path(workspace).is_dir():
            messagebox.showwarning(APP, "This project has no workspace.")
            return
        project_path = str(self.project.path)

        def done(result):
            if result["errors"]:
                lines = ["%s:%s: %s" % (path, line, message)
                         for path, line, message in result["errors"]]
                messagebox.showwarning(
                    APP, "%d rewrite problem(s):\n%s" % (
                        len(lines), "\n".join(lines[:10])))
                self.status.set("%d rewrite problem(s)." % len(lines))
                return
            self.status.set("Applied %d translations." % result["applied"])
            messagebox.showinfo(APP, "Applied %d translations." %
                                result["applied"])

        self._start_job("Applying translations...",
                        lambda: _apply_project(project_path, workspace),
                        done)

    def build_project(self):
        if self.project is None:
            return
        workspace = self.project.get_meta("workspace")
        if not workspace or not Path(workspace).is_dir():
            messagebox.showwarning(APP, "This project has no workspace.")
            return
        output = filedialog.askdirectory(
            title="Select an empty output folder")
        if not output:
            return
        project_path = str(self.project.path)
        settings = dict(self.settings)

        def done(destination):
            self.status.set("Build ready: %s" % destination)
            messagebox.showinfo(APP, "Build ready:\n%s" % destination)

        self._start_job("Building translated mod...",
                        lambda: _build_project(project_path, workspace,
                                               output, settings),
                        done)

    def validate_project(self):
        if self.project is None:
            return
        problems = []
        for row in self.project.strings():
            for problem in validate(row["original"], row["translation"]):
                problems.append("%s:%s: %s" % (row["relative_path"],
                                               row["line"], problem))
        if problems:
            messagebox.showwarning(
                APP, "%d validation problem(s):\n%s" % (
                    len(problems), "\n".join(problems[:10])))
        else:
            messagebox.showinfo(APP, "No validation problems.")
        self.status.set("%d validation problem(s)." % len(problems))

    def export_csv(self):
        if self.project is None:
            return
        path = filedialog.asksaveasfilename(
            title="Export strings", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(("id", "file", "line", "original",
                             "translation", "context", "status"))
            for row in self.project.strings():
                writer.writerow((row["id"], row["relative_path"], row["line"],
                                 row["original"], row["translation"],
                                 row["context"], row["status"]))
        self.status.set("Exported to %s." % path)

    def import_csv(self):
        if self.project is None:
            return
        path = filedialog.askopenfilename(
            title="Import translations", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        count = 0
        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("id") and row.get("translation") is not None:
                    self.project.set_translation(int(row["id"]),
                                                 row["translation"])
                    count += 1
        self._reload_rows()
        self.status.set("Imported %d translations." % count)

    def show_settings(self):
        SettingsDialog(self, self.settings, self._apply_settings)

    def _apply_settings(self, settings):
        self.settings = settings
        self.status.set("Settings saved.")

    def destroy(self):
        if self.project is not None:
            self.project.close()
            self.project = None
        super().destroy()

    def _close(self):
        self.destroy()


def run(project_path=None):
    app = TranslationApp(project_path)
    app.mainloop()

