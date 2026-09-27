"""
Olynax OS 5.0 — Установщик + встроенная ОС (всё в одном файле)
Запусти: python olynax.py
"""

import os
import sys
import json
import shutil
import hashlib
import getpass
import subprocess
from datetime import datetime

VERSION = "5.0"
CODENAME = "Wolf"
INSTALL_DIR = os.path.join(os.path.expanduser("~"), ".olynax_os")


# ============================================================
#  ВСТРОЕННЫЙ КОД OLYNAX OS (записывается в папку установки)
# ============================================================
OLYNAX_OS_CODE = r'''"""
Olynax OS 5.0 - Графическая оболочка (окна ВНУТРИ ОС)
"""

import customtkinter as ctk
import tkinter as tk
from datetime import datetime
import json
import os
import hashlib
import sys

VERSION = "5.0"
CODENAME = "Wolf"
THEME_COLOR = "#4a7fff"
DARK_BG = "#0d0d12"
WINDOW_BG = "#1a1a22"
TOPBAR_BG = "#16161c"
DOCK_BG = "#22222c"

INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(INSTALL_DIR, "users.json")
SYSTEM_FILE = os.path.join(INSTALL_DIR, "system.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def hash_password(p, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 100000)
    return salt, h.hex()


def verify_password(p, salt, stored):
    _, h = hash_password(p, salt)
    return h == stored


# ==================== ВСТРОЕННОЕ ОКНО ====================
class EmbeddedWindow(ctk.CTkFrame):
    """Окно, которое живёт ВНУТРИ главного окна ОС."""

    def __init__(self, master, os_app, title, width=680, height=460):
        super().__init__(master, fg_color=WINDOW_BG, corner_radius=12,
                         border_width=1, border_color="#2f2f3f")

        self.os_app = os_app
        self.win_width = width
        self.win_height = height
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_maximized = False
        self.original_geometry = (0, 0, width, height)

        # Позиция по центру
        parent_w = master.winfo_width() or 1280
        parent_h = master.winfo_height() or 800
        x = max(20, (parent_w - width) // 2)
        y = max(40, (parent_h - height) // 2)

        self.place(x=x, y=y, width=width, height=height)
        self.lift()

        # ===== ЗАГОЛОВОК =====
        header = ctk.CTkFrame(self, height=36, fg_color="#252530",
                              corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Кнопки macOS
        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(side="left", padx=10)

        ctk.CTkButton(btns, text="", width=13, height=13, corner_radius=10,
                      fg_color="#ff5f56", hover_color="#ff3b30",
                      command=self.close).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="", width=13, height=13, corner_radius=10,
                      fg_color="#ffbd2e", hover_color="#ffaa00",
                      command=self.minimize).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="", width=13, height=13, corner_radius=10,
                      fg_color="#27c93f", hover_color="#1aad2e",
                      command=self.maximize).pack(side="left", padx=3)

        # Заголовок
        self.title_label = ctk.CTkLabel(header, text=title,
                                         font=("Arial", 13),
                                         text_color="#cccccc")
        self.title_label.pack(side="left", padx=20)

        # ===== ТЕЛО =====
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== ПЕРЕТАСКИВАНИЕ =====
        for w in (header, self.title_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)

        # Поднять при клике
        self.bind("<Button-1>", lambda e: self.lift())

    def _start_drag(self, event):
        self.drag_start_x = event.x_root - self.winfo_x()
        self.drag_start_y = event.y_root - self.winfo_y()
        self.lift()

    def _do_drag(self, event):
        if self.is_maximized:
            return
        new_x = event.x_root - self.drag_start_x
        new_y = event.y_root - self.drag_start_y
        parent_w = self.master.winfo_width() or 1280
        parent_h = self.master.winfo_height() or 800
        new_x = max(0, min(new_x, parent_w - 100))
        new_y = max(0, min(new_y, parent_h - 50))
        self.place(x=new_x, y=new_y)

    def close(self):
        self.os_app.remove_window(self)
        self.destroy()

    def minimize(self):
        self.os_app.minimize_window(self)

    def maximize(self):
        if self.is_maximized:
            x, y, w, h = self.original_geometry
            self.place(x=x, y=y, width=w, height=h)
            self.is_maximized = False
        else:
            self.original_geometry = (self.winfo_x(), self.winfo_y(),
                                       self.win_width, self.win_height)
            self.place(x=0, y=0,
                       width=self.master.winfo_width(),
                       height=self.master.winfo_height())
            self.is_maximized = True


# ==================== ЭКРАН ВХОДА ====================
class LoginScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Olynax OS {VERSION} - Вход")
        self.geometry("900x600")
        self.resizable(False, False)
        self.configure(fg_color=DARK_BG)

        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                self.user = json.load(f)
        except Exception:
            self.user = None
        self.failed = 0
        self._build()

    def _build(self):
        left = ctk.CTkFrame(self, fg_color="#16161c", width=400, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="\U0001F43A", font=("Arial", 96)).pack(pady=(80, 8))
        ctk.CTkLabel(left, text=f"Olynax OS {VERSION}",
                     font=("Arial", 24, "bold"),
                     text_color="#ffffff").pack()
        ctk.CTkLabel(left, text=f"{CODENAME} Edition",
                     font=("Arial", 13),
                     text_color=THEME_COLOR).pack(pady=(4, 0))
        ctk.CTkLabel(left, text="Сила волка. Элегантность яблока.",
                     font=("Arial", 11, "italic"),
                     text_color="#8888aa").pack(pady=(8, 0))

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        fn = self.user.get("fullname", "User") if self.user else "Гость"
        un = self.user.get("username", "user") if self.user else "guest"

        ctk.CTkLabel(right, text=f"\U0001F464 {fn}",
                     font=("Arial", 22, "bold"),
                     text_color="#ffffff").pack(pady=(100, 4))
        ctk.CTkLabel(right, text=f"@{un}",
                     font=("Arial", 13),
                     text_color="#8888aa").pack(pady=(0, 30))

        self.pwd = ctk.CTkEntry(right, show="\u25CF",
                                 placeholder_text="Введите пароль...",
                                 font=("Arial", 14),
                                 fg_color="#0a0a0f",
                                 text_color="#ffffff",
                                 border_color="#333344",
                                 height=44, width=320)
        self.pwd.pack(pady=8)
        self.pwd.bind("<Return>", lambda e: self._login())
        self.pwd.focus()

        self.msg = ctk.CTkLabel(right, text="", font=("Arial", 11),
                                 text_color="#ff6666")
        self.msg.pack(pady=4)

        ctk.CTkButton(right, text="Войти ->",
                      font=("Arial", 14, "bold"),
                      fg_color=THEME_COLOR, hover_color="#3a6fe0",
                      width=320, height=44,
                      command=self._login).pack(pady=16)

        ctk.CTkButton(right, text="Выключить",
                      fg_color="transparent", hover_color="#2a2a35",
                      text_color="#8888aa",
                      width=120, height=32,
                      command=self.destroy).pack(side="bottom", pady=20)

    def _login(self):
        if not self.user:
            self._launch()
            return
        if verify_password(self.pwd.get(),
                           self.user["password_salt"],
                           self.user["password_hash"]):
            self._launch()
        else:
            self.failed += 1
            self.msg.configure(text=f"Неверный пароль ({self.failed})")
            self.pwd.delete(0, "end")

    def _launch(self):
        self.destroy()
        OlynaxOS().mainloop()


# ==================== ГЛАВНАЯ ОС ====================
class OlynaxOS(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Olynax OS {VERSION} - {CODENAME} Edition")
        self.geometry("1280x800")
        self.minsize(900, 600)
        self.configure(fg_color=DARK_BG)

        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                self.user = json.load(f)
        except Exception:
            self.user = {"username": "wolf", "fullname": "User",
                         "wallpaper": "gradient_blue"}

        self.state_data = self._load_state()
        self.open_windows = {}
        self.minimized_windows = []

        # Верхняя панель
        self._build_topbar()

        # Контейнер рабочего стола (именно тут живут окна)
        self.desktop = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=0)
        self.desktop.pack(fill="both", expand=True)

        # Обои и иконки
        self._build_wallpaper()
        self._build_desktop_icons()

        # Док
        self._build_dock()

    def _load_state(self):
        sf = os.path.join(INSTALL_DIR, "state.json")
        if os.path.exists(sf):
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"fileSystem": {"system5": {"type": "folder", "items": {}}},
                "currentPath": ["system5"], "savesCount": 0, "notes": ""}

    def _save_state(self):
        self.state_data["savesCount"] = self.state_data.get("savesCount", 0) + 1
        with open(os.path.join(INSTALL_DIR, "state.json"), "w",
                  encoding="utf-8") as f:
            json.dump(self.state_data, f, ensure_ascii=False, indent=2)

    # -------- Управление окнами --------
    def _open_window(self, key, title, w=680, h=460):
        if key in self.open_windows:
            win = self.open_windows[key]
            try:
                if win.winfo_exists():
                    win.lift()
                    if key in self.minimized_windows:
                        self.minimized_windows.remove(key)
                        win.place(x=win.original_geometry[0],
                                  y=win.original_geometry[1],
                                  width=win.win_width,
                                  height=win.win_height)
                    return win
            except Exception:
                pass

        if key in self.minimized_windows:
            self.minimized_windows.remove(key)

        win = EmbeddedWindow(self.desktop, self, title, w, h)
        self.open_windows[key] = win
        return win

    def remove_window(self, win):
        for key, w in list(self.open_windows.items()):
            if w == win:
                del self.open_windows[key]
                if key in self.minimized_windows:
                    self.minimized_windows.remove(key)
                break

    def minimize_window(self, win):
        for key, w in list(self.open_windows.items()):
            if w == win:
                win.place_forget()
                if key not in self.minimized_windows:
                    self.minimized_windows.append(key)
                break

    # -------- Верхняя панель --------
    def _build_topbar(self):
        tb = ctk.CTkFrame(self, height=34, fg_color=TOPBAR_BG, corner_radius=0)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)

        ctk.CTkLabel(tb, text="\U0001F43A", font=("Arial", 18)).pack(side="left", padx=(12, 4))

        for name, cmd in [("Olynax", self.open_about),
                          ("Файл", None), ("Вид", None), ("Окно", None)]:
            ctk.CTkButton(tb, text=name, font=("Arial", 12),
                          fg_color="transparent", hover_color="#2a2a35",
                          text_color="#dddddd", width=65, height=26,
                          command=cmd).pack(side="left", padx=2)

        right = ctk.CTkFrame(tb, fg_color="transparent")
        right.pack(side="right", padx=10)

        self.clock = ctk.CTkLabel(right, text="", font=("Arial", 12),
                                   text_color="#dddddd")
        self.clock.pack(side="right", padx=8)
        ctk.CTkLabel(right, text=f"\U0001F464 {self.user.get('fullname', 'User')}",
                     font=("Arial", 12),
                     text_color="#dddddd").pack(side="right", padx=8)
        ctk.CTkLabel(right, text="\U0001F50B 92%", font=("Arial", 12),
                     text_color="#dddddd").pack(side="right", padx=8)

        self._tick()

    def _tick(self):
        now = datetime.now()
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        months = ["янв", "фев", "мар", "апр", "мая", "июн",
                  "июл", "авг", "сен", "окт", "ноя", "дек"]
        self.clock.configure(
            text=f"{days[now.weekday()]} {now.day} {months[now.month-1]}  "
                 f"{now.strftime('%H:%M')}")
        self.after(1000, self._tick)

    # -------- Обои --------
    def _build_wallpaper(self):
        wp = ctk.CTkFrame(self.desktop, fg_color="transparent")
        wp.place(relx=0, rely=0, relwidth=1, relheight=1)
        wp.lower()
        canvas = tk.Canvas(wp, highlightthickness=0, bd=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        wallpaper = self.user.get("wallpaper", "gradient_blue")
        colors = {
            "gradient_blue": ((15, 25, 50), (40, 60, 120)),
            "gradient_purple": ((30, 15, 50), (70, 40, 120)),
            "gradient_dark": ((10, 10, 15), (30, 30, 40)),
            "gradient_wolf": ((35, 15, 15), (80, 30, 30)),
        }
        c1, c2 = colors.get(wallpaper, colors["gradient_blue"])

        def redraw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            for i in range(h):
                r_ = i / h
                r = int(c1[0] + (c2[0] - c1[0]) * r_)
                g = int(c1[1] + (c2[1] - c1[1]) * r_)
                b = int(c1[2] + (c2[2] - c1[2]) * r_)
                canvas.create_line(0, i, w, i, fill=f"#{r:02x}{g:02x}{b:02x}")

        canvas.bind("<Configure>", redraw)

        ctk.CTkLabel(wp, text=f"Olynax OS {VERSION}",
                     font=("Arial", 64, "bold"),
                     text_color="#ffffff").place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(wp, text=f"Добро пожаловать, {self.user.get('fullname', 'User')}!",
                     font=("Arial", 16),
                     text_color="#aabbff").place(relx=0.5, rely=0.5, anchor="center")

    # -------- Иконки --------
    def _build_desktop_icons(self):
        frame = ctk.CTkFrame(self.desktop, fg_color="transparent")
        frame.place(x=20, y=20)
        frame.lift()

        icons = [
            ("\U0001F4C1", "Finder", self.open_finder),
            ("\U0001F4BB", "Терминал", self.open_terminal),
            ("\U0001F9EE", "Калькулятор", self.open_calculator),
            ("\U0001F4DD", "Заметки", self.open_notes),
            ("\u2699", "Настройки", self.open_settings),
            ("\U0001F43A", "Об Olynax", self.open_about),
        ]

        for emoji, label, cmd in icons:
            item = ctk.CTkFrame(frame, fg_color="transparent",
                                width=80, height=95)
            item.pack(side="top", anchor="nw", pady=4)
            item.pack_propagate(False)
            ctk.CTkButton(item, text=emoji, width=64, height=64,
                          font=("Arial", 34),
                          fg_color="#1f1f2a", hover_color="#2f2f3a",
                          corner_radius=14, command=cmd).pack(pady=(4, 2))
            ctk.CTkLabel(item, text=label, font=("Arial", 11),
                         text_color="#e0e0e0").pack()

    # -------- Док --------
    def _build_dock(self):
        cont = ctk.CTkFrame(self, fg_color="transparent", height=90)
        cont.pack(fill="x", side="bottom")
        cont.pack_propagate(False)

        dock = ctk.CTkFrame(cont, height=72, corner_radius=22,
                            fg_color=DOCK_BG, border_width=1,
                            border_color="#2f2f3f")
        dock.pack(pady=10, padx=200, fill="x")
        dock.pack_propagate(False)

        items = [
            ("\U0001F4C1", self.open_finder),
            ("\U0001F4BB", self.open_terminal),
            ("\U0001F9EE", self.open_calculator),
            ("\U0001F4DD", self.open_notes),
            ("\U0001F43A", self.open_about),
            ("\u2699", self.open_settings),
            ("|", None),
            ("\u23FB", self.shutdown),
        ]
        for emoji, cmd in items:
            if emoji == "|":
                ctk.CTkFrame(dock, width=1, height=40,
                             fg_color="#3a3a4a").pack(side="left", padx=8, pady=16)
                continue
            ctk.CTkButton(dock, text=emoji, width=52, height=52,
                          font=("Arial", 26),
                          fg_color="transparent", hover_color="#33333f",
                          corner_radius=12, command=cmd).pack(side="left", padx=4, pady=10)

    # -------- Приложения --------
    def open_finder(self):
        win = self._open_window("finder", "Finder", 720, 500)
        for w in win.body.winfo_children():
            w.destroy()
        ctk.CTkLabel(win.body, text=f"\U0001F4C2 {INSTALL_DIR}",
                     font=("Courier", 12),
                     text_color="#8888aa").pack(anchor="w")
        grid = ctk.CTkScrollableFrame(win.body)
        grid.pack(fill="both", expand=True, pady=8)
        try:
            for name in sorted(os.listdir(INSTALL_DIR)):
                path = os.path.join(INSTALL_DIR, name)
                icon = "\U0001F4C1" if os.path.isdir(path) else "\U0001F4C4"
                item = ctk.CTkFrame(grid, fg_color="#22222c",
                                    corner_radius=10, width=110, height=110)
                item.pack(side="left", padx=6, pady=6)
                item.pack_propagate(False)
                ctk.CTkLabel(item, text=icon, font=("Arial", 34)).pack(pady=(8, 0))
                ctk.CTkLabel(item, text=name[:14], font=("Arial", 10),
                             text_color="#dddddd").pack()
        except Exception as e:
            ctk.CTkLabel(win.body, text=f"Ошибка: {e}").pack()

    def open_terminal(self):
        win = self._open_window("terminal", "Терминал", 760, 500)
        for w in win.body.winfo_children():
            w.destroy()
        out = ctk.CTkTextbox(win.body, fg_color="#000000",
                             text_color="#00ff88",
                             font=("Courier New", 13))
        out.pack(fill="both", expand=True, pady=(0, 8))
        out.insert("end", f"Olynax OS {VERSION} Terminal\n")
        out.insert("end", "Команды: help, ver, whoami, date, pwd, exit\n")
        out.insert("end", "-" * 50 + "\n")
        out.configure(state="disabled")

        inp = ctk.CTkFrame(win.body, fg_color="transparent")
        inp.pack(fill="x")
        ctk.CTkLabel(inp, text="$", font=("Courier New", 14, "bold"),
                     text_color=THEME_COLOR).pack(side="left", padx=(0, 6))
        entry = ctk.CTkEntry(inp, fg_color="#0a0a0f",
                             text_color="#00ff88", font=("Courier New", 13))
        entry.pack(fill="x", expand=True)
        entry.focus()

        def append(t):
            out.configure(state="normal")
            out.insert("end", t + "\n")
            out.configure(state="disabled")
            out.see("end")

        def run(e=None):
            cmd = entry.get().strip()
            entry.delete(0, "end")
            if not cmd:
                return
            append(f"$ {cmd}")
            c = cmd.lower()
            if c == "help":
                append("help  ver  whoami  date  pwd  echo  exit")
            elif c == "ver":
                append(f"Olynax OS {VERSION} ({CODENAME})")
            elif c == "whoami":
                append(self.user.get("username", "wolf"))
            elif c == "date":
                append(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
            elif c == "pwd":
                append(INSTALL_DIR)
            elif c.startswith("echo "):
                append(cmd[5:])
            elif c == "exit":
                win.close()
            else:
                append(f"Неизвестная команда: {c}")

        entry.bind("<Return>", run)

    def open_calculator(self):
        win = self._open_window("calc", "Калькулятор", 340, 500)
        for w in win.body.winfo_children():
            w.destroy()
        disp = ctk.CTkEntry(win.body, font=("Courier New", 26, "bold"),
                            justify="right", height=60, fg_color="#0a0a0f",
                            text_color="#ffffff", border_color="#333344")
        disp.pack(fill="x", pady=(0, 12))
        disp.insert(0, "0")
        st = {"e": "", "r": "0"}

        def upd():
            disp.delete(0, "end")
            disp.insert(0, st["e"] or st["r"])

        def press(v):
            if v == "C":
                st["e"] = ""; st["r"] = "0"
            elif v == "DEL":
                st["e"] = st["e"][:-1]
            elif v == "=":
                if not st["e"]:
                    return
                try:
                    ex = st["e"].replace("x", "*").replace("/", "/")
                    if not all(c in "0123456789.+-*/() " for c in ex):
                        raise ValueError()
                    st["r"] = str(eval(ex, {"__builtins__": {}}, {}))
                    st["e"] = ""
                except Exception:
                    st["r"] = "Ошибка"; st["e"] = ""
            else:
                st["e"] += v
            upd()

        grid = ctk.CTkFrame(win.body)
        grid.pack(fill="both", expand=True)
        buttons = [["C", "(", ")", "/"], ["7", "8", "9", "*"],
                   ["4", "5", "6", "-"], ["1", "2", "3", "+"],
                   ["0", ".", "DEL", "="]]
        for r, row in enumerate(buttons):
            grid.rowconfigure(r, weight=1)
            for ci, lab in enumerate(row):
                grid.columnconfigure(ci, weight=1)
                fg = ("#ff5f56" if lab == "C" else
                      THEME_COLOR if lab == "=" else
                      "#ffbd2e" if lab == "DEL" else
                      "#3a3a4a" if lab in "/*-+()" else "#22222c")
                ctk.CTkButton(grid, text=lab, font=("Arial", 20, "bold"),
                              fg_color=fg, corner_radius=10,
                              command=lambda x=lab: press(x)).grid(
                    row=r, column=ci, padx=4, pady=4, sticky="nsew")

    def open_notes(self):
        win = self._open_window("notes", "Заметки", 600, 460)
        for w in win.body.winfo_children():
            w.destroy()
        ctk.CTkLabel(win.body, text="Мои заметки",
                     font=("Arial", 16, "bold")).pack(anchor="w")
        txt = ctk.CTkTextbox(win.body, fg_color="#0a0a0f")
        txt.pack(fill="both", expand=True, pady=8)
        txt.insert("1.0", self.state_data.get("notes", ""))
        status = ctk.CTkLabel(win.body, text="", text_color="#00ff88")

        def save():
            self.state_data["notes"] = txt.get("1.0", "end-1c")
            self._save_state()
            status.configure(text="Сохранено")

        btn = ctk.CTkFrame(win.body, fg_color="transparent")
        btn.pack(fill="x")
        ctk.CTkButton(btn, text="Сохранить", fg_color=THEME_COLOR,
                      command=save).pack(side="left")
        status.pack(side="right")

    def open_settings(self):
        win = self._open_window("settings", "Настройки", 600, 500)
        for w in win.body.winfo_children():
            w.destroy()
        ctk.CTkLabel(win.body, text="Настройки",
                     font=("Arial", 20, "bold")).pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(win.body, text=f"Версия: Olynax OS {VERSION}",
                     font=("Arial", 12)).pack(anchor="w")
        ctk.CTkLabel(win.body, text=f"Пользователь: {self.user.get('username', 'wolf')}",
                     font=("Arial", 12)).pack(anchor="w")
        ctk.CTkLabel(win.body, text=f"Путь: {INSTALL_DIR}",
                     font=("Arial", 11),
                     text_color="#8888aa").pack(anchor="w", pady=8)

        def logout():
            self._save_state()
            self.destroy()
            LoginScreen().mainloop()

        ctk.CTkButton(win.body, text="Выйти из системы",
                      fg_color="#5a4a2a", hover_color="#7a5a3a",
                      command=logout).pack(anchor="w", pady=8)

    def open_about(self):
        win = self._open_window("about", "Об Olynax OS", 500, 440)
        for w in win.body.winfo_children():
            w.destroy()
        ctk.CTkLabel(win.body, text="\U0001F43A", font=("Arial", 64)).pack(pady=(16, 8))
        ctk.CTkLabel(win.body, text=f"Olynax OS {VERSION}",
                     font=("Arial", 26, "bold")).pack()
        ctk.CTkLabel(win.body, text=f"{CODENAME} Edition",
                     font=("Arial", 14), text_color=THEME_COLOR).pack()
        ctk.CTkLabel(win.body, text="Сила волка. Элегантность яблока.",
                     font=("Arial", 12, "italic"),
                     text_color="#8888aa").pack(pady=12)
        ctk.CTkLabel(win.body,
                     text=f"Пользователь: {self.user.get('username', 'wolf')}\n"
                          f"Путь: {INSTALL_DIR}",
                     font=("Courier", 11),
                     text_color="#666688").pack(pady=8)

    def shutdown(self):
        self._save_state()
        ov = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        ov.place(relx=0, rely=0, relwidth=1, relheight=1)
        ov.lift()
        ctk.CTkLabel(ov, text="\u23FB", font=("Arial", 64),
                     text_color=THEME_COLOR).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(ov, text="Выключение Olynax OS...",
                     font=("Arial", 18),
                     text_color="#888").place(relx=0.5, rely=0.52, anchor="center")
        self.after(1500, self.destroy)


def main():
    if not os.path.exists(SYSTEM_FILE):
        print("Olynax OS не установлена!")
        sys.exit(1)
    LoginScreen().mainloop()


if __name__ == "__main__":
    main()
'''


# ============================================================
#  УСТАНОВЩИК
# ============================================================
def hash_password(pwd):
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt.encode(), 100000)
    return salt, h.hex()


def check_installed():
    return os.path.exists(os.path.join(INSTALL_DIR, "system.json"))


def install():
    print("=" * 55)
    print(f"  Olynax OS {VERSION} ({CODENAME}) - Установка")
    print("=" * 55)
    print()

    if check_installed():
        print(f"Olynax OS уже установлена в:")
        print(f"  {INSTALL_DIR}")
        print()
        ans = input("Переустановить? (y/n): ").strip().lower()
        if ans != "y":
            print()
            launch_os()
            return
        print("Удаляю старую систему...")
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)

    os.makedirs(INSTALL_DIR, exist_ok=True)
    print(f"OK Папка: {INSTALL_DIR}")

    # Записываем файл ОС
    os_file = os.path.join(INSTALL_DIR, "olynax_os.py")
    with open(os_file, "w", encoding="utf-8") as f:
        f.write(OLYNAX_OS_CODE)
    print(f"OK Записан: olynax_os.py")

    print()
    username = input("  Имя пользователя [wolf]: ").strip() or "wolf"
    fullname = input("  Полное имя [Olynax User]: ").strip() or "Olynax User"

    while True:
        pwd = getpass.getpass("  Пароль (мин. 4 символа): ")
        if len(pwd) < 4:
            print("  Пароль слишком короткий")
            continue
        pwd2 = getpass.getpass("  Повторите пароль: ")
        if pwd != pwd2:
            print("  Пароли не совпадают")
            continue
        break

    salt, pwd_hash = hash_password(pwd)
    print("OK Пароль установлен")

    files = {
        "system.json": {
            "version": VERSION, "codename": CODENAME,
            "installed_at": datetime.now().isoformat(),
            "install_path": INSTALL_DIR,
        },
        "users.json": {
            "username": username, "fullname": fullname,
            "password_salt": salt, "password_hash": pwd_hash,
            "wallpaper": "gradient_blue",
            "created_at": datetime.now().isoformat(),
        },
        "config.json": {
            "first_launch": False,
            "wallpaper": "gradient_blue",
            "theme": "dark",
        },
        "registry.json": {},
        "state.json": {
            "fileSystem": {"system5": {"type": "folder", "items": {}}},
            "currentPath": ["system5"],
            "savesCount": 0, "notes": "",
        },
    }

    for name, data in files.items():
        with open(os.path.join(INSTALL_DIR, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"OK Создан: {name}")

    for folder in ["apps", "app_data", "desktop", "bin", "drivers"]:
        os.makedirs(os.path.join(INSTALL_DIR, folder), exist_ok=True)

    print()
    print("=" * 55)
    print(f"  Olynax OS {VERSION} успешно установлена!")
    print("=" * 55)
    print(f"  Папка:        {INSTALL_DIR}")
    print(f"  Пользователь: {username}")
    print()

    ans = input("Запустить Olynax OS сейчас? (y/n): ").strip().lower()
    if ans == "y":
        launch_os()
    else:
        print(f"\nЗапустить позже:")
        print(f'  python "{os_file}"')
        print()


def launch_os():
    os_file = os.path.join(INSTALL_DIR, "olynax_os.py")
    if not os.path.exists(os_file):
        print("Файл ОС не найден!")
        return
    print(f"\nЗапуск Olynax OS...\n")
    subprocess.Popen([sys.executable, os_file])


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--help", "-h"):
            print(f"""
Olynax OS {VERSION} - один файл делает всё

  python olynax.py             установка + запуск
  python olynax.py --run       только запуск ОС
  python olynax.py --reset     удалить систему
  python olynax.py --status    статус
""")
            return
        if arg == "--run":
            if not check_installed():
                print("Система не установлена.")
                return
            launch_os()
            return
        if arg == "--reset":
            if os.path.exists(INSTALL_DIR):
                shutil.rmtree(INSTALL_DIR, ignore_errors=True)
                print("OK Система удалена")
            else:
                print("Система и так не установлена")
            return
        if arg == "--status":
            if check_installed():
                with open(os.path.join(INSTALL_DIR, "system.json"),
                          encoding="utf-8") as f:
                    d = json.load(f)
                print(f"OK Olynax OS установлена")
                print(f"   Версия: {d['version']} ({d['codename']})")
                print(f"   Путь:   {d['install_path']}")
            else:
                print("X Не установлена")
            return

    install()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано\n")
    except Exception as e:
        print(f"\nОшибка: {e}\n")
        import traceback
        traceback.print_exc()