import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path

BG = "#1e1e1e"
BG2 = "#252525"
BG3 = "#2d2d2d"
FG = "#d4d4d4"
FG_DIM = "#888888"
FG_HI = "#ce9178"
ACCENT = "#e34527"
SEL_BG = "#094771"
ENTRY = "#3c3c3c"


def apply_dark_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        ".",
        background=BG,
        foreground=FG,
        fieldbackground=ENTRY,
        bordercolor=BG3,
        troughcolor=BG2,
        selectbackground=SEL_BG,
        selectforeground=FG,
        font=("Segoe UI", 9),
    )

    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)

    style.configure(
        "TCombobox",
        fieldbackground=ENTRY,
        background=ENTRY,
        foreground=FG,
        arrowcolor=FG,
        selectbackground=ENTRY,
        selectforeground=FG,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", ENTRY)],
        selectbackground=[("readonly", ENTRY)],
        selectforeground=[("readonly", FG)],
    )

    style.configure(
        "TScrollbar", background=BG3, troughcolor=BG2, arrowcolor=FG_DIM, bordercolor=BG
    )
    style.map("TScrollbar", background=[("active", "#555555")])

    style.configure(
        "Treeview",
        background=BG2,
        foreground=FG,
        fieldbackground=BG2,
        rowheight=22,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading", background=BG3, foreground=FG, relief="flat", borderwidth=0
    )
    style.map(
        "Treeview", background=[("selected", SEL_BG)], foreground=[("selected", FG)]
    )


DEFAULT_PUB_DIR = Path.home()

CATEGORY_FOLDERS = {
    "Items": "items",
    "NPCs": "npcs",
    "Classes": "classes",
    "Spells": "spells",
    "Shops": "shops",
    "Inns": "inns",
    "Skill Masters": "skill_masters",
}

# Fields to show in the list view for each category
LIST_FIELDS = {
    "Items": ["name", "type", "subtype", "weight", "graphic_id"],
    "NPCs": ["name", "type", "level", "hp", "experience"],
    "Classes": ["name", "parent_type", "stat_group"],
    "Spells": ["name", "type", "sp_cost", "tp_cost", "hp_heal"],
    "Shops": ["name"],
    "Inns": ["name"],
    "Skill Masters": ["name"],
}


class EOJson(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EOJson")
        self.geometry("1100x700")
        self.configure(bg=BG)
        apply_dark_theme(self)

        icon_path = Path(__file__).parent / "eojson-icon.png"
        if icon_path.exists():
            icon = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, icon)
            self._icon = icon  # keep reference

        self.pub_dir = DEFAULT_PUB_DIR
        self.current_file = None
        self.current_data = None
        self.field_vars = {}
        self.records = []

        self._build_ui()
        self.after(100, self._prompt_dir)

    def _build_ui(self):
        # Left panel
        left = tk.Frame(self, bg=BG, width=400)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(8, 4), pady=8)
        left.pack_propagate(False)

        # Category selector
        cat_frame = tk.Frame(left, bg=BG)
        cat_frame.pack(fill=tk.X, pady=(0, 6))

        tk.Button(
            cat_frame,
            text="📁 Open pub dir",
            command=self._choose_dir,
            bg=BG3,
            fg=FG,
            relief="flat",
            padx=8,
            pady=2,
            activebackground="#444444",
            activeforeground=FG,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            cat_frame,
            text="About",
            command=self._show_about,
            bg=BG3,
            fg=FG,
            relief="flat",
            padx=8,
            pady=2,
            activebackground="#444444",
            activeforeground=FG,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Label(cat_frame, text="Category:", bg=BG, fg=FG).pack(side=tk.LEFT)
        self.cat_var = tk.StringVar(value="Items")
        cat_menu = ttk.Combobox(
            cat_frame,
            textvariable=self.cat_var,
            values=list(CATEGORY_FOLDERS.keys()),
            state="readonly",
            width=18,
        )
        cat_menu.pack(side=tk.LEFT, padx=6)
        cat_menu.bind(
            "<<ComboboxSelected>>", lambda e: self._load_category(self.cat_var.get())
        )

        search_frame = tk.Frame(left, bg=BG)
        search_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(search_frame, text="Search:", bg=BG, fg=FG).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_list())
        tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=ENTRY,
            fg=FG,
            insertbackground=FG,
            relief="flat",
        ).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

        # List
        list_frame = tk.Frame(left, bg=BG)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            list_frame, columns=("id", "name"), show="headings", selectmode="browse"
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=300)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Right panel
        right = tk.Frame(self, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

        self.file_label = tk.Label(right, text="", bg=BG, fg=FG_DIM, anchor="w")
        self.file_label.pack(fill=tk.X, pady=(0, 4))

        canvas = tk.Canvas(right, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right, orient="vertical", command=canvas.yview)
        self.fields_frame = tk.Frame(canvas, bg=BG)

        self.fields_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.fields_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(e):
            if canvas.winfo_height() >= self.fields_frame.winfo_reqheight():
                return
            canvas.yview_scroll(-1 * (e.delta // 120), "units")

        canvas.bind(
            "<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel)
        )
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # Bottom bar
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)
        tk.Button(
            btn_frame,
            text="Save",
            command=self._save,
            bg=ACCENT,
            fg="white",
            relief="flat",
            activebackground="#c73b20",
            activeforeground="white",
            padx=20,
            pady=4,
        ).pack(side=tk.RIGHT)
        self.status = tk.Label(btn_frame, text="", bg=BG, fg="#88cc88", anchor="w")
        self.status.pack(side=tk.LEFT)

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title("About EOjson")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        icon_path = Path(__file__).parent / "eojson-icon.png"
        if icon_path.exists():
            icon = tk.PhotoImage(file=str(icon_path))
            # Scale down to ~64px
            w, h = icon.width(), icon.height()
            scale = max(w, h) // 64 or 1
            icon = icon.subsample(scale, scale)
            tk.Label(win, image=icon, bg=BG).pack(pady=(16, 4))
            win._icon = icon

        tk.Label(win, text="EOJson", bg=BG, fg=FG, font=("Segoe UI", 16, "bold")).pack()
        tk.Label(
            win,
            text="A JSON pub file editor for endless online server software that allows json pubs to be used.",
            bg=BG,
            fg=FG_DIM,
            font=("Segoe UI", 9),
        ).pack(pady=(2, 12))

        def link(parent, text, url):
            lbl = tk.Label(
                parent,
                text=text,
                bg=BG,
                fg="#4da6ff",
                font=("Segoe UI", 9, "underline"),
                cursor="hand2",
            )
            lbl.pack(pady=2)
            lbl.bind("<Button-1>", lambda e: __import__("webbrowser").open(url))

        link(
            win,
            "EOJson — github.com/jimmysnetwork/eojson/",
            "https://github.com/jimmysnetwork/eojson/",
        )
        link(
            win,
            "pub2json — github.com/sorokya/pub2json",
            "https://github.com/sorokya/pub2json",
        )

        tk.Button(
            win,
            text="Close",
            command=win.destroy,
            bg=ACCENT,
            fg="white",
            relief="flat",
            padx=16,
            pady=4,
            activebackground="#c73b20",
            activeforeground="white",
        ).pack(pady=16)

    def _prompt_dir(self):
        messagebox.showinfo(
            "Welcome to EOjson",
            "Please select your pub JSON directory to get started.\n\n"
            "This should be the folder containing items/, npcs/, classes/, etc.",
        )
        self._choose_dir()

    def _choose_dir(self):
        chosen = filedialog.askdirectory(
            title="Select pub directory", initialdir=str(self.pub_dir)
        )
        if chosen:
            self.pub_dir = Path(chosen)
            self._load_category(self.cat_var.get())

    def _load_category(self, category):
        self.current_category = category
        self.current_file = None
        self.current_data = None
        self.search_var.set("")
        self._clear_fields()

        folder = self.pub_dir / CATEGORY_FOLDERS[category]
        self.records = []
        if folder.exists():
            for f in sorted(folder.glob("*.json")):
                try:
                    data = json.loads(f.read_text())
                    record_id = int(f.stem)
                    self.records.append((record_id, data.get("name", ""), f, data))
                except Exception:
                    pass

        self._populate_list(self.records)
        self.title(f"EOJson — {self.pub_dir}")

    def _populate_list(self, records):
        self.tree.delete(*self.tree.get_children())
        for record_id, name, path, data in records:
            self.tree.insert("", "end", iid=str(path), values=(record_id, name))

    def _filter_list(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self._populate_list(self.records)
            return

        # Search current category
        filtered = [
            (rid, name, path, data)
            for rid, name, path, data in self.records
            if query in name.lower() or query in str(rid)
        ]

        # If nothing found, search all other categories
        if not filtered:
            for cat, folder_name in CATEGORY_FOLDERS.items():
                if cat == self.current_category:
                    continue
                folder = self.pub_dir / folder_name
                if not folder.exists():
                    continue
                for f in sorted(folder.glob("*.json")):
                    try:
                        data = json.loads(f.read_text())
                        name = data.get("name", "")
                        rid = int(f.stem)
                        if query in name.lower() or query in str(rid):
                            filtered.append((rid, name, f, data))
                    except Exception:
                        pass
                if filtered:
                    self.current_category = cat
                    self.cat_var.set(cat)
                    self.records = []
                    for f in sorted(folder.glob("*.json")):
                        try:
                            d = json.loads(f.read_text())
                            self.records.append((int(f.stem), d.get("name", ""), f, d))
                        except Exception:
                            pass
                    break

        self._populate_list(filtered)

        # Auto-select if exactly one result
        if len(filtered) == 1:
            iid = str(filtered[0][2])
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self._on_select(None)

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        path = Path(selection[0])
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file:\n{e}")
            return
        self.current_file = path
        self.current_data = data
        self.file_label.config(text=str(path.name))
        self._render_fields(data)
        self.status.config(text="")

    def _clear_fields(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.field_vars.clear()

    def _render_fields(self, data):
        self._clear_fields()

        highlight = LIST_FIELDS.get(self.current_category, [])

        # Sort: highlighted fields first, then alphabetical
        keys = sorted(data.keys(), key=lambda k: (k not in highlight, k))

        for i, key in enumerate(keys):
            value = data[key]
            row_bg = BG if i % 2 == 0 else BG2
            row = tk.Frame(self.fields_frame, bg=row_bg)
            row.pack(fill=tk.X, padx=4, pady=1)

            label_fg = FG_HI if key in highlight else FG_DIM
            tk.Label(row, text=key, bg=row_bg, fg=label_fg, width=22, anchor="w").pack(
                side=tk.LEFT, padx=(4, 8)
            )

            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                cb = tk.Checkbutton(
                    row,
                    variable=var,
                    bg=row_bg,
                    activebackground=row_bg,
                    selectcolor=ENTRY,
                    fg=FG,
                    activeforeground=FG,
                )
                cb.pack(side=tk.LEFT)
                self.field_vars[key] = ("bool", var)

            elif isinstance(value, list):
                text = tk.Text(
                    row,
                    height=max(2, min(len(value) * 2, 8)),
                    width=55,
                    bg=ENTRY,
                    fg=FG,
                    insertbackground=FG,
                    relief="flat",
                    font=("Consolas", 9),
                )
                text.insert("1.0", json.dumps(value, indent=2))
                text.pack(side=tk.LEFT, padx=2, pady=2)
                self.field_vars[key] = ("list", text)

            else:
                var = tk.StringVar(value=str(value))
                entry = tk.Entry(
                    row,
                    textvariable=var,
                    bg=ENTRY,
                    fg=FG,
                    insertbackground=FG,
                    relief="flat",
                    width=30,
                )
                entry.pack(side=tk.LEFT, padx=2)
                self.field_vars[key] = ("str", var, type(value))

    def _save(self):
        if not self.current_file or not self.current_data:
            return

        new_data = {}
        try:
            for key, info in self.field_vars.items():
                kind = info[0]
                if kind == "bool":
                    new_data[key] = info[1].get()
                elif kind == "list":
                    new_data[key] = json.loads(info[1].get("1.0", tk.END))
                else:
                    raw = info[1].get()
                    orig_type = info[2]
                    if orig_type == int:
                        new_data[key] = int(raw)
                    elif orig_type == float:
                        new_data[key] = float(raw)
                    else:
                        new_data[key] = raw
        except Exception as e:
            messagebox.showerror("Validation Error", str(e))
            return

        self.current_file.write_text(json.dumps(new_data, indent=2))
        self.current_data = new_data

        # Update name in list
        name = new_data.get("name", "")
        record_id = int(self.current_file.stem)
        for item in self.records:
            if item[2] == self.current_file:
                idx = self.records.index(item)
                self.records[idx] = (record_id, name, self.current_file, new_data)
                break
        self.tree.item(str(self.current_file), values=(record_id, name))
        self._show_toast(f"Saved {self.current_file.name}")

    def _show_toast(self, message):
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.92)
        toast.configure(bg="#2d6a3f")

        tk.Label(
            toast,
            text=f"✓  {message}",
            bg="#2d6a3f",
            fg="white",
            font=("Segoe UI", 10),
            padx=16,
            pady=10,
        ).pack()

        # Position bottom-right of main window
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() - 280
        y = self.winfo_y() + self.winfo_height() - 70
        toast.geometry(f"+{x}+{y}")

        def fade(alpha=0.92):
            alpha -= 0.05
            if alpha <= 0:
                toast.destroy()
                return
            toast.attributes("-alpha", alpha)
            toast.after(40, lambda: fade(alpha))

        toast.after(1200, fade)


if __name__ == "__main__":
    app = EOJson()
    app.mainloop()
