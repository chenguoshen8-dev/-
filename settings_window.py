"""Settings window with glassmorphism, API management, and connection test."""
import tkinter as tk
from tkinter import ttk
import json, threading, urllib.request, copy

from config import save_cfg
from glass_effect import apply_acrylic


class SettingsWindow(tk.Toplevel):
    NAV = [("API", "⚡"), ("桌宠", "✨"), ("系统", "⚙"), ("关于", "ℹ")]

    BG = '#F5F5FA'
    SIDEBAR_BG = '#EDEDF2'
    ACCENT = '#D97757'
    BORDER = '#E5E5EA'
    TEXT = '#1C1C1E'
    TEXT_SEC = '#888'

    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.cfg = copy.deepcopy(cfg)
        self.on_save = on_save
        self.title("小钳设置")
        self.geometry("680x460")
        self.resizable(False, False)
        self.configure(bg=self.BG)

        apply_acrylic(self)

        self._build()
        self._show_page(0)

    def _build(self):
        nav = tk.Frame(self, bg=self.SIDEBAR_BG, width=140)
        nav.pack(side='left', fill='y')
        nav.pack_propagate(False)

        self._nav_btns = []
        for i, (label, icon) in enumerate(self.NAV):
            btn = tk.Button(nav, text=f"  {icon}  {label}", anchor='w',
                            bg=self.SIDEBAR_BG, relief='flat', font=('微软雅黑', 11),
                            fg=self.TEXT, activebackground='#DBDBE5',
                            command=lambda i=i: self._show_page(i))
            btn.pack(fill='x', pady=1, padx=4)
            self._nav_btns.append(btn)

        self._content = tk.Frame(self, bg=self.BG)
        self._content.pack(side='left', fill='both', expand=True)

        self._pages = {
            0: self._page_api(),
            1: self._page_pet(),
            2: self._page_system(),
            3: self._page_about(),
        }

    def _show_page(self, idx):
        for i, btn in enumerate(self._nav_btns):
            btn.config(bg=self.ACCENT if i == idx else self.SIDEBAR_BG,
                       fg='white' if i == idx else self.TEXT)
        for page in self._pages.values():
            page.pack_forget()
        self._pages[idx].pack(fill='both', expand=True, padx=20, pady=16)

    # ── API page ────────────────────────────────
    def _page_api(self):
        f = tk.Frame(self._content, bg=self.BG)
        tk.Label(f, text="API 配置", font=('微软雅黑', 15, 'bold'), bg=self.BG).pack(anchor='w')
        tk.Label(f, text="配置 API 端点，在对话框顶部下拉切换",
                 font=('微软雅黑', 9), fg=self.TEXT_SEC, bg=self.BG).pack(anchor='w', pady=(0, 10))

        nb = tk.Frame(f, bg=self.BG)
        nb.pack(fill='both', expand=True)

        tab_bar = tk.Frame(nb, bg=self.BG)
        tab_bar.pack(fill='x')
        tab_content = tk.Frame(nb, bg=self.BG)
        tab_content.pack(fill='both', expand=True, pady=(6, 0))

        self._api_tabs = []
        self._api_frames = []
        self._api_vars = []

        for i in range(3):
            api = self.cfg['apis'][i]
            vars_ = {
                'name': tk.StringVar(value=api.get('name', f'API {i + 1}')),
                'url': tk.StringVar(value=api.get('url', '')),
                'key': tk.StringVar(value=api.get('key', '')),
                'model': tk.StringVar(value=api.get('model', '')),
            }
            for k, v in vars_.items():
                v.trace_add('write', lambda *a, idx=i, k=k, v=v: self.cfg['apis'][idx].update({k: v.get()}))
            self._api_vars.append(vars_)

            tab_btn = tk.Button(tab_bar, text=f"  {api.get('name', f'API {i + 1}')}  ",
                                relief='flat', font=('微软雅黑', 10),
                                command=lambda i=i: self._show_api_tab(i))
            tab_btn.pack(side='left', padx=2)
            self._api_tabs.append(tab_btn)

            pf = tk.Frame(tab_content, bg=self.BG)
            for label, key, show in [("名称", "name", ''), ("API URL", "url", ''),
                                      ("API Key", "key", ''), ("模型", "model", '')]:
                row = tk.Frame(pf, bg=self.BG)
                row.pack(fill='x', pady=4)
                tk.Label(row, text=label, width=9, anchor='w', font=('微软雅黑', 10),
                         bg=self.BG, fg='#444').pack(side='left')
                e = tk.Entry(row, textvariable=vars_[key], font=('微软雅黑', 10),
                             relief='solid', bd=1, bg='white', show=show)
                e.pack(side='left', fill='x', expand=True, ipady=4)

            # test connection button
            test_row = tk.Frame(pf, bg=self.BG)
            test_row.pack(fill='x', pady=8)
            status_lbl = tk.Label(test_row, text='', font=('微软雅黑', 9), bg=self.BG)
            status_lbl.pack(side='left', padx=4)
            tk.Button(test_row, text='测试连接', font=('微软雅黑', 9),
                      bg=self.ACCENT, fg='white', relief='flat', padx=12, pady=4,
                      command=lambda i=i, sl=status_lbl: self._test_connection(i, sl)
                      ).pack(side='left')

            self._api_frames.append(pf)

        self._show_api_tab(0)

        tk.Button(f, text="保存", bg=self.ACCENT, fg='white', relief='flat',
                  font=('微软雅黑', 10), padx=20, pady=5,
                  command=self._save).pack(anchor='w', pady=(10, 0))
        return f

    def _show_api_tab(self, idx):
        for i, (btn, frame) in enumerate(zip(self._api_tabs, self._api_frames)):
            sel = i == idx
            btn.config(bg=self.ACCENT if sel else '#E0E0E0', fg='white' if sel else self.TEXT)
            if sel:
                frame.pack(fill='both', expand=True, pady=4)
            else:
                frame.pack_forget()

    def _test_connection(self, idx, status_lbl):
        status_lbl.config(text='测试中...', fg=self.TEXT_SEC)
        api = self.cfg['apis'][idx]
        threading.Thread(target=self._do_test, args=(api, status_lbl), daemon=True).start()

    def _do_test(self, api, status_lbl):
        try:
            data = json.dumps({
                "model": api.get('model', 'gpt-4o'),
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5,
            }).encode()
            req = urllib.request.Request(
                api['url'], data=data,
                headers={"Authorization": f"Bearer {api['key']}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                json.loads(r.read().decode())
            self.after(0, lambda: status_lbl.config(text='✓ 连接成功', fg='#2E7D32'))
        except Exception as e:
            self.after(0, lambda: status_lbl.config(text=f'✗ 失败: {str(e)[:40]}', fg='#C62828'))

    # ── pet page ─────────────────────────────────
    def _page_pet(self):
        f = tk.Frame(self._content, bg=self.BG)
        tk.Label(f, text="桌宠设置", font=('微软雅黑', 15, 'bold'), bg=self.BG).pack(anchor='w')

        row = tk.Frame(f, bg=self.BG)
        row.pack(anchor='w', pady=10)
        tk.Label(row, text="大小倍率", font=('微软雅黑', 10), bg=self.BG, width=10, anchor='w').pack(side='left')
        size_var = tk.IntVar(value=self.cfg['pet_size'])
        tk.Scale(row, from_=2, to=6, orient='horizontal', variable=size_var,
                 bg=self.BG, length=160,
                 command=lambda v: self.cfg.update({'pet_size': int(v)})).pack(side='left')

        row2 = tk.Frame(f, bg=self.BG)
        row2.pack(anchor='w', pady=4)
        tk.Label(row2, text="始终置顶", font=('微软雅黑', 10), bg=self.BG, width=10, anchor='w').pack(side='left')
        top_var = tk.BooleanVar(value=self.cfg['topmost'])
        tk.Checkbutton(row2, variable=top_var, bg=self.BG,
                       command=lambda: self.cfg.update({'topmost': top_var.get()})).pack(side='left')

        tk.Button(f, text="保存", bg=self.ACCENT, fg='white', relief='flat',
                  font=('微软雅黑', 10), padx=20, pady=5,
                  command=self._save).pack(anchor='w', pady=(16, 0))
        return f

    def _page_system(self):
        f = tk.Frame(self._content, bg=self.BG)
        tk.Label(f, text="系统", font=('微软雅黑', 15, 'bold'), bg=self.BG).pack(anchor='w')
        tk.Button(f, text="退出桌宠", bg='#E8472A', fg='white', relief='flat',
                  font=('微软雅黑', 10), padx=16, pady=5,
                  command=self.master.destroy).pack(anchor='w', pady=20)
        return f

    def _page_about(self):
        f = tk.Frame(self._content, bg=self.BG)
        tk.Label(f, text="关于", font=('微软雅黑', 15, 'bold'), bg=self.BG).pack(anchor='w')
        tk.Label(f, text="Claude 星星桌宠 v2.0\n基于 Claude API 驱动\n✨ 星芒像素形象",
                 font=('微软雅黑', 10), fg='#555', bg=self.BG, justify='left').pack(anchor='w', pady=12)
        return f

    def _save(self):
        save_cfg(self.cfg)
        self.on_save(self.cfg)
        self.destroy()
