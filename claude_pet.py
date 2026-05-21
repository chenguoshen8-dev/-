import tkinter as tk
from tkinter import scrolledtext, ttk
import random, threading, urllib.request, json, sys, os, ctypes, queue, re

_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\ClaudeCrabPet_Singleton")
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'claude_pet_cfg.json')

DEFAULT_CFG = {
    "active_api": 0,
    "apis": [
        {"name": "shaco.chat", "url": "https://shaco.chat/api/v1/chat/completions",
         "key": "cr_0a94bf16076372457f108dddf52f0226f67bdf7d7c34e36580b41e0c2ccf726a", "model": "claude-opus-4-7"},
        {"name": "API 2", "url": "", "key": "", "model": ""},
        {"name": "API 3", "url": "", "key": "", "model": ""},
    ],
    "pet_size": 3,
    "topmost": True,
}

def load_cfg():
    try:
        with open(CFG_FILE, encoding='utf-8') as f:
            d = json.load(f)
            return {**DEFAULT_CFG, **d}
    except:
        return dict(DEFAULT_CFG)

def save_cfg(cfg):
    with open(CFG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── 设置窗口 ──────────────────────────────────────────
class SettingsWindow(tk.Toplevel):
    NAV = [("API 配置", "🤖"), ("桌宠", "🐾"), ("系统", "⚙"), ("关于", "ℹ")]

    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.cfg = json.loads(json.dumps(cfg))  # deep copy
        self.on_save = on_save
        self.title("小钳设置")
        self.geometry("660x440")
        self.resizable(False, False)
        self.attributes('-topmost', True)
        self.configure(bg='#F5F5F7')
        self._build()
        self._show_page(0)

    def _build(self):
        nav = tk.Frame(self, bg='#ECECEC', width=150)
        nav.pack(side='left', fill='y')
        nav.pack_propagate(False)
        self._nav_btns = []
        for i, (label, icon) in enumerate(self.NAV):
            btn = tk.Button(nav, text=f"  {icon}  {label}", anchor='w',
                            bg='#ECECEC', relief='flat', font=('微软雅黑', 11),
                            fg='#333', activebackground='#D0D0D0',
                            command=lambda i=i: self._show_page(i))
            btn.pack(fill='x', pady=1, padx=4)
            self._nav_btns.append(btn)

        self._content = tk.Frame(self, bg='#F5F5F7')
        self._content.pack(side='left', fill='both', expand=True)
        self._pages = {
            0: self._page_api(),
            1: self._page_pet(),
            2: self._page_system(),
            3: self._page_about(),
        }

    def _show_page(self, idx):
        for i, btn in enumerate(self._nav_btns):
            btn.config(bg='#4A90E2' if i == idx else '#ECECEC',
                       fg='white' if i == idx else '#333')
        for page in self._pages.values():
            page.pack_forget()
        self._pages[idx].pack(fill='both', expand=True, padx=20, pady=16)

    def _page_api(self):
        f = tk.Frame(self._content, bg='#F5F5F7')
        tk.Label(f, text="API 配置", font=('微软雅黑', 15, 'bold'), bg='#F5F5F7').pack(anchor='w')
        tk.Label(f, text="配置最多 3 组 API，在对话框中切换使用", font=('微软雅黑', 9), fg='#888', bg='#F5F5F7').pack(anchor='w', pady=(0, 10))

        nb = tk.Frame(f, bg='#F5F5F7')
        nb.pack(fill='both', expand=True)

        tab_bar = tk.Frame(nb, bg='#F5F5F7')
        tab_bar.pack(fill='x')
        tab_content = tk.Frame(nb, bg='#F5F5F7')
        tab_content.pack(fill='both', expand=True, pady=(6, 0))

        self._api_tabs = []
        self._api_frames = []
        self._api_vars = []

        for i in range(3):
            api = self.cfg['apis'][i]
            vars_ = {
                'name':  tk.StringVar(value=api.get('name', f'API {i+1}')),
                'url':   tk.StringVar(value=api.get('url', '')),
                'key':   tk.StringVar(value=api.get('key', '')),
                'model': tk.StringVar(value=api.get('model', '')),
            }
            for k, v in vars_.items():
                v.trace_add('write', lambda *a, idx=i, k=k, v=v: self.cfg['apis'][idx].update({k: v.get()}))
            self._api_vars.append(vars_)

            tab_btn = tk.Button(tab_bar, text=f"  {api.get('name', f'API {i+1}')}  ",
                                relief='flat', font=('微软雅黑', 10),
                                command=lambda i=i: self._show_api_tab(i))
            tab_btn.pack(side='left', padx=2)
            self._api_tabs.append(tab_btn)

            pf = tk.Frame(tab_content, bg='#F5F5F7')
            for label, key, show in [("名称", "name", ''), ("API URL", "url", ''), ("API Key", "key", ''), ("模型", "model", '')]:
                row = tk.Frame(pf, bg='#F5F5F7')
                row.pack(fill='x', pady=4)
                tk.Label(row, text=label, width=9, anchor='w', font=('微软雅黑', 10), bg='#F5F5F7', fg='#444').pack(side='left')
                e = tk.Entry(row, textvariable=vars_[key], font=('微软雅黑', 10),
                             relief='solid', bd=1, bg='white', show=show)
                e.pack(side='left', fill='x', expand=True, ipady=4)
            self._api_frames.append(pf)

        self._show_api_tab(0)

        tk.Button(f, text="保存", bg='#4A90E2', fg='white', relief='flat',
                  font=('微软雅黑', 10), padx=20, pady=5,
                  command=self._save).pack(anchor='w', pady=(10, 0))
        return f

    def _show_api_tab(self, idx):
        for i, (btn, frame) in enumerate(zip(self._api_tabs, self._api_frames)):
            sel = i == idx
            btn.config(bg='#4A90E2' if sel else '#E0E0E0', fg='white' if sel else '#333')
            if sel:
                frame.pack(fill='both', expand=True, pady=4)
            else:
                frame.pack_forget()

    def _page_pet(self):
        f = tk.Frame(self._content, bg='#F5F5F7')
        tk.Label(f, text="桌宠设置", font=('微软雅黑', 15, 'bold'), bg='#F5F5F7').pack(anchor='w')

        row = tk.Frame(f, bg='#F5F5F7')
        row.pack(anchor='w', pady=10)
        tk.Label(row, text="大小倍率", font=('微软雅黑', 10), bg='#F5F5F7', width=10, anchor='w').pack(side='left')
        size_var = tk.IntVar(value=self.cfg['pet_size'])
        tk.Scale(row, from_=2, to=6, orient='horizontal', variable=size_var,
                 bg='#F5F5F7', length=160,
                 command=lambda v: self.cfg.update({'pet_size': int(v)})).pack(side='left')

        row2 = tk.Frame(f, bg='#F5F5F7')
        row2.pack(anchor='w', pady=4)
        tk.Label(row2, text="始终置顶", font=('微软雅黑', 10), bg='#F5F5F7', width=10, anchor='w').pack(side='left')
        top_var = tk.BooleanVar(value=self.cfg['topmost'])
        tk.Checkbutton(row2, variable=top_var, bg='#F5F5F7',
                       command=lambda: self.cfg.update({'topmost': top_var.get()})).pack(side='left')

        tk.Button(f, text="保存", bg='#4A90E2', fg='white', relief='flat',
                  font=('微软雅黑', 10), padx=20, pady=5,
                  command=self._save).pack(anchor='w', pady=(16, 0))
        return f

    def _page_system(self):
        f = tk.Frame(self._content, bg='#F5F5F7')
        tk.Label(f, text="系统", font=('微软雅黑', 15, 'bold'), bg='#F5F5F7').pack(anchor='w')
        tk.Button(f, text="退出桌宠", bg='#E8472A', fg='white', relief='flat',
                  font=('微软雅黑', 10), padx=16, pady=5,
                  command=self.master.destroy).pack(anchor='w', pady=20)
        return f

    def _page_about(self):
        f = tk.Frame(self._content, bg='#F5F5F7')
        tk.Label(f, text="关于", font=('微软雅黑', 15, 'bold'), bg='#F5F5F7').pack(anchor='w')
        tk.Label(f, text="Claude 螃蟹桌宠 v1.1\n基于 Claude API 驱动\n像素风官方形象",
                 font=('微软雅黑', 10), fg='#555', bg='#F5F5F7', justify='left').pack(anchor='w', pady=12)
        return f

    def _save(self):
        save_cfg(self.cfg)
        self.on_save(self.cfg)
        self.destroy()


# ── 对话窗口 ──────────────────────────────────────────
class ChatWindow(tk.Toplevel):
    BG       = '#FFFFFF'
    BG_MSG   = '#F7F7F8'
    USER_BG  = '#EBF3FF'
    BOT_BG   = '#F7F7F8'
    ACCENT   = '#D77757'
    THINK_BG = '#FFF8E7'

    def __init__(self, parent, cfg, history, on_reply=None):
        super().__init__(parent)
        self.cfg = cfg
        self.history = history
        self.on_reply = on_reply
        self.busy = False
        self._q = queue.Queue()
        self._stream_mark = None   # Text index where current stream starts
        self._think_visible = {}   # msg_id -> bool
        self.title("🦀 小钳")
        self.geometry("600x700")
        self.minsize(480, 500)
        self.configure(bg=self.BG)
        self._build()
        self._replay_history()
        self._poll()
        self.entry.focus()

    # ── 布局 ──
    def _build(self):
        # 顶栏
        top = tk.Frame(self, bg='#1C1C1E', pady=8)
        top.pack(fill='x')
        tk.Label(top, text="🦀  小钳", font=('微软雅黑', 12, 'bold'),
                 bg='#1C1C1E', fg='white').pack(side='left', padx=14)

        # 模型/API 选择
        right_top = tk.Frame(top, bg='#1C1C1E')
        right_top.pack(side='right', padx=10)
        self._api_var = tk.StringVar()
        names = [a['name'] for a in self.cfg['apis']]
        cb = ttk.Combobox(right_top, textvariable=self._api_var, values=names,
                          width=14, state='readonly', font=('微软雅黑', 9))
        cb.pack(side='right')
        cb.set(names[self.cfg.get('active_api', 0)])
        cb.bind('<<ComboboxSelected>>', self._switch_api)

        # 消息滚动区
        outer = tk.Frame(self, bg=self.BG)
        outer.pack(fill='both', expand=True)
        self._canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)
        self._msg_frame = tk.Frame(self._canvas, bg=self.BG)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._msg_frame, anchor='nw')
        self._msg_frame.bind('<Configure>', self._on_frame_resize)
        self._canvas.bind('<Configure>', self._on_canvas_resize)
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # 分隔线
        tk.Frame(self, bg='#E5E5EA', height=1).pack(fill='x')

        # 底部输入区（仿 Claude.ai）
        bottom = tk.Frame(self, bg='#F2F2F7', pady=10)
        bottom.pack(fill='x', padx=12)

        input_wrap = tk.Frame(bottom, bg='white', relief='solid', bd=1)
        input_wrap.pack(fill='x')

        self.entry = tk.Text(input_wrap, font=('微软雅黑', 11), relief='flat', bd=0,
                             bg='white', height=3, wrap=tk.WORD, padx=10, pady=8)
        self.entry.pack(fill='x', expand=True)
        self.entry.insert('1.0', '')
        self._set_placeholder()
        self.entry.bind('<FocusIn>',  self._clear_placeholder)
        self.entry.bind('<FocusOut>', self._set_placeholder)
        self.entry.bind('<Return>',   self._on_enter)

        toolbar = tk.Frame(input_wrap, bg='white', pady=4)
        toolbar.pack(fill='x', padx=8)

        # + 按钮
        tk.Button(toolbar, text='+', font=('Arial', 14), bg='white', fg='#888',
                  relief='flat', bd=0, cursor='hand2',
                  command=lambda: None).pack(side='left')

        # 清空
        tk.Button(toolbar, text='清空对话', font=('微软雅黑', 9), bg='white', fg='#888',
                  relief='flat', bd=0, cursor='hand2',
                  command=self._clear).pack(side='left', padx=8)

        # 发送按钮（圆形橙色）
        self.send_btn = tk.Canvas(toolbar, width=32, height=32, bg='white',
                                  highlightthickness=0, cursor='hand2')
        self.send_btn.pack(side='right')
        self._draw_send_btn(active=True)
        self.send_btn.bind('<Button-1>', lambda e: self._send())

    def _draw_send_btn(self, active=True):
        self.send_btn.delete('all')
        color = self.ACCENT if active else '#CCC'
        self.send_btn.create_oval(2, 2, 30, 30, fill=color, outline='')
        # 上箭头
        self.send_btn.create_polygon(16, 8, 10, 20, 16, 17, 22, 20,
                                     fill='white', outline='')

    def _set_placeholder(self, e=None):
        if not self.entry.get('1.0', 'end-1c').strip():
            self.entry.delete('1.0', tk.END)
            self.entry.insert('1.0', 'Write a message...')
            self.entry.config(fg='#AAAAAA')

    def _clear_placeholder(self, e=None):
        if self.entry.get('1.0', 'end-1c') == 'Write a message...':
            self.entry.delete('1.0', tk.END)
            self.entry.config(fg='#111111')

    def _on_enter(self, e):
        if not (e.state & 0x1):
            self._send()
            return 'break'

    def _on_frame_resize(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def _on_canvas_resize(self, e):
        self._canvas.itemconfig(self._canvas_win, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(int(-1*(e.delta/120)), 'units')

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    def _switch_api(self, e=None):
        name = self._api_var.get()
        for i, a in enumerate(self.cfg['apis']):
            if a['name'] == name:
                self.cfg['active_api'] = i
                break

    # ── 消息气泡 ──
    def _add_bubble(self, role, text='', thinking=''):
        is_user = role == 'user'
        outer = tk.Frame(self._msg_frame, bg=self.BG, pady=4)
        outer.pack(fill='x', padx=12)

        if is_user:
            bubble = tk.Frame(outer, bg=self.USER_BG, padx=14, pady=10)
            bubble.pack(anchor='e')
            lbl = tk.Label(bubble, text=text, font=('微软雅黑', 10),
                           bg=self.USER_BG, fg='#1C1C1E', wraplength=380, justify='left')
            lbl.pack(anchor='w')
            return None, None

        # AI 气泡
        row = tk.Frame(outer, bg=self.BG)
        row.pack(fill='x')
        tk.Label(row, text='🦀', font=('Arial', 16), bg=self.BG).pack(side='left', anchor='n', padx=(0,8))

        right = tk.Frame(row, bg=self.BG)
        right.pack(side='left', fill='x', expand=True)
        tk.Label(right, text='小钳', font=('微软雅黑', 9, 'bold'),
                 bg=self.BG, fg='#888').pack(anchor='w')

        # 思考过程（可折叠）
        think_frame = None
        if thinking:
            think_toggle = tk.Frame(right, bg=self.BG)
            think_toggle.pack(anchor='w', pady=(2,0))
            self._think_visible[id(think_toggle)] = False
            think_body = tk.Frame(right, bg=self.THINK_BG, padx=10, pady=6)
            tk.Label(think_body, text=thinking, font=('微软雅黑', 9), fg='#888',
                     bg=self.THINK_BG, wraplength=380, justify='left').pack(anchor='w')

            def toggle(tb=think_body, tt=think_toggle, key=id(think_toggle)):
                self._think_visible[key] = not self._think_visible[key]
                if self._think_visible[key]:
                    tb.pack(anchor='w', fill='x', pady=(0,4))
                    for w in tt.winfo_children(): w.destroy()
                    tk.Label(tt, text='▼ 思考过程', font=('微软雅黑', 9), fg=self.ACCENT,
                             bg=self.BG, cursor='hand2').pack(side='left')
                else:
                    tb.pack_forget()
                    for w in tt.winfo_children(): w.destroy()
                    tk.Label(tt, text='▶ 思考过程', font=('微软雅黑', 9), fg=self.ACCENT,
                             bg=self.BG, cursor='hand2').pack(side='left')
                self._scroll_bottom()

            tk.Label(think_toggle, text='▶ 思考过程', font=('微软雅黑', 9), fg=self.ACCENT,
                     bg=self.BG, cursor='hand2').pack(side='left')
            think_toggle.bind('<Button-1>', lambda e: toggle())
            for w in think_toggle.winfo_children():
                w.bind('<Button-1>', lambda e: toggle())

        # 回复文本（用 Text widget 支持流式追加）
        bubble = tk.Frame(right, bg=self.BOT_BG, padx=14, pady=10)
        bubble.pack(anchor='w', fill='x')
        txt = tk.Text(bubble, font=('微软雅黑', 10), bg=self.BOT_BG, fg='#1C1C1E',
                      relief='flat', bd=0, wrap=tk.WORD, height=1,
                      state='normal', cursor='arrow')
        txt.pack(fill='x')
        txt.tag_config('bold', font=('微软雅黑', 10, 'bold'))
        txt.tag_config('code', font=('Consolas', 9), background='#EFEFEF', foreground='#C7254E')
        if text:
            self._insert_rich(txt, text)
            txt.config(state='disabled')
            self._auto_height(txt)
        return txt, bubble

    def _insert_rich(self, txt, text):
        # 简单 markdown：**bold** 和 `code`
        parts = re.split(r'(\*\*.*?\*\*|`[^`]+`)', text)
        for p in parts:
            if p.startswith('**') and p.endswith('**'):
                txt.insert(tk.END, p[2:-2], 'bold')
            elif p.startswith('`') and p.endswith('`'):
                txt.insert(tk.END, p[1:-1], 'code')
            else:
                txt.insert(tk.END, p)

    def _auto_height(self, txt):
        txt.update_idletasks()
        lines = int(txt.index(tk.END).split('.')[0])
        txt.config(height=max(1, lines - 1))

    # ── 历史回放 ──
    def _replay_history(self):
        for msg in self.history:
            self._add_bubble(msg['role'], msg['content'])
        self._scroll_bottom()

    # ── 发送 ──
    def _send(self):
        text = self.entry.get('1.0', tk.END).strip()
        if not text or text == 'Write a message...' or self.busy:
            return
        self.entry.delete('1.0', tk.END)
        self._set_placeholder()
        self._add_bubble('user', text)
        self.history.append({"role": "user", "content": text})
        self.busy = True
        self._draw_send_btn(active=False)

        # 占位 AI 气泡
        self._stream_txt, _ = self._add_bubble('assistant', '')
        self._scroll_bottom()

        threading.Thread(target=self._stream_ask, daemon=True).start()

    def _stream_ask(self):
        idx = self.cfg.get('active_api', 0)
        api = self.cfg['apis'][idx]
        if not api.get('url') or not api.get('key'):
            self._q.put(('token', '请先在设置中配置 API URL 和 Key'))
            self._q.put(('done', ''))
            return
        system = "你是一只可爱的螃蟹桌宠，名叫「小钳」，说话简短可爱，偶尔用螃蟹动作描述自己。"
        messages = [{"role": "system", "content": system}] + self.history
        data = json.dumps({"model": api.get('model', 'gpt-4o'),
                           "messages": messages, "max_tokens": 800,
                           "stream": True}).encode()
        req = urllib.request.Request(
            api['url'], data=data,
            headers={"Authorization": f"Bearer {api['key']}",
                     "Content-Type": "application/json"})
        full = ''
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                for raw in r:
                    line = raw.decode('utf-8').strip()
                    if not line.startswith('data:'):
                        continue
                    chunk = line[5:].strip()
                    if chunk == '[DONE]':
                        break
                    try:
                        delta = json.loads(chunk)['choices'][0]['delta']
                        token = delta.get('content') or delta.get('reasoning_content', '')
                        if token:
                            full += token
                            self._q.put(('token', token))
                    except:
                        pass
        except Exception as e:
            self._q.put(('token', f'\n*挥钳* 出错了：{e}'))
        self._q.put(('done', full))

    def _poll(self):
        try:
            while True:
                kind, val = self._q.get_nowait()
                if kind == 'token' and self._stream_txt:
                    self._stream_txt.config(state='normal')
                    self._stream_txt.insert(tk.END, val)
                    self._auto_height(self._stream_txt)
                    self._scroll_bottom()
                elif kind == 'done':
                    if self._stream_txt:
                        self._stream_txt.config(state='disabled')
                    full = val
                    self.history.append({"role": "assistant", "content": full})
                    self.busy = False
                    self._draw_send_btn(active=True)
                    if self.on_reply:
                        self.on_reply(full)
        except queue.Empty:
            pass
        self.after(30, self._poll)

    def _clear(self):
        self.history.clear()
        for w in self._msg_frame.winfo_children():
            w.destroy()
        self._scroll_bottom()


# ── 桌宠主体 ──────────────────────────────────────────
class CrabPet:
    def __init__(self):
        self.cfg = load_cfg()
        self.history = []

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', self.cfg['topmost'])
        self.root.attributes('-transparentcolor', '#010101')
        self.root.configure(bg='#010101')

        self.W, self.H = 120, 110
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H,
                                bg='#010101', highlightthickness=0)
        self.canvas.pack()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.x = float(sw - 160)
        self.y = float(sh - 150)

        self.vx = 1.5
        self.frame = 0
        self.state = 'walk'
        self.state_timer = 120
        self.blink_timer = 100
        self.blinking = False
        self.happy_timer = 0
        self.dragging = False
        self.drag_ox = self.drag_oy = 0
        self.bubble_text = ""
        self.bubble_timer = 0

        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<B1-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.canvas.bind('<Button-3>', self._show_menu)
        self.canvas.bind('<Double-Button-1>', lambda e: self._open_chat())

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label='💬 和我说话', command=self._open_chat)
        self.menu.add_command(label='⚙ 设置',     command=self._open_settings)
        self.menu.add_separator()
        self.menu.add_command(label='退出',        command=self.root.destroy)

        self._chat_win = None
        self._update()
        self.root.mainloop()

    def _on_click(self, e):
        self.dragging = True
        self.drag_ox, self.drag_oy = e.x, e.y
        self._do_happy()

    def _on_drag(self, e):
        if self.dragging:
            self.x += e.x - self.drag_ox
            self.y += e.y - self.drag_oy
            self.root.geometry(f'{self.W}x{self.H}+{int(self.x)}+{int(self.y)}')

    def _on_release(self, e):
        self.dragging = False

    def _show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def _do_happy(self):
        self.state = 'happy'
        self.happy_timer = 60

    def _open_chat(self):
        if self._chat_win and self._chat_win.winfo_exists():
            self._chat_win.lift()
            self._chat_win.focus()
            return
        def on_reply(text):
            self.bubble_text = text[:30] + ("…" if len(text) > 30 else "")
            self.bubble_timer = 200
            self._do_happy()
        self._chat_win = ChatWindow(self.root, self.cfg, self.history, on_reply)

    def _open_settings(self):
        def on_save(new_cfg):
            self.cfg = new_cfg
            self.root.attributes('-topmost', new_cfg['topmost'])
        SettingsWindow(self.root, self.cfg, on_save)

    def _update(self):
        self.frame += 1
        sw = self.root.winfo_screenwidth()

        if not self.dragging:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = random.choice(['walk', 'walk', 'idle'])
                self.state_timer = random.randint(80, 200)
                if self.state == 'walk':
                    self.vx = random.choice([-1, 1]) * random.uniform(1, 2.5)
            if self.happy_timer > 0:
                self.state = 'happy'
                self.happy_timer -= 1
            if self.state == 'walk':
                self.x += self.vx
                if self.x < 0:           self.x = 0;           self.vx = abs(self.vx)
                if self.x > sw - self.W: self.x = sw - self.W; self.vx = -abs(self.vx)
            self.root.geometry(f'{self.W}x{self.H}+{int(self.x)}+{int(self.y)}')

        if self.bubble_timer > 0:
            self.bubble_timer -= 1

        self.blink_timer -= 1
        if self.blink_timer <= 0:
            self.blinking = not self.blinking
            self.blink_timer = 5 if self.blinking else random.randint(80, 180)

        self._draw()
        self.root.after(33, self._update)

    def _draw(self):
        c = self.canvas
        c.delete('all')
        f = self.frame
        P = max(2, self.cfg.get('pet_size', 3))
        cx, cy = self.W // 2, self.H // 2 + 10
        COL  = '#D77757'
        DARK = '#A85535'

        def px(gx, gy, col=COL):
            x0 = cx + gx * P
            y0 = cy + gy * P
            c.create_rectangle(x0, y0, x0+P-1, y0+P-1, fill=col, outline='')

        happy = self.state == 'happy'

        if self.bubble_timer > 0 and self.bubble_text:
            bx, by = cx, cy - 55
            tw = min(len(self.bubble_text) * 7 + 20, 210)
            c.create_rectangle(bx-tw//2, by-15, bx+tw//2, by+15,
                                fill='white', outline='#CCC', width=1)
            c.create_polygon(cx-5, by+15, cx+5, by+15, cx, by+23,
                             fill='white', outline='#CCC')
            c.create_text(bx, by, text=self.bubble_text, fill='#333',
                          font=('微软雅黑', 8), width=tw-10)

        phase = int(f * 0.3) % 2 if self.state == 'walk' else 0
        for i, col_idx in enumerate([0, 1, 4, 5]):
            lift = -1 if phase == i % 2 else 0
            px(col_idx - 3, 3 + lift)
            px(col_idx - 3, 4 + lift)

        for gx in range(-3, 3):
            for gy in range(0, 2):
                px(gx, gy)

        for gx in [-3, 2]:
            px(gx, -1, DARK)

        for gx in [-3, 2]:
            if not self.blinking:
                px(gx, -2)
            else:
                x0 = cx + gx * P
                y0 = cy + (-2) * P + P // 3
                c.create_rectangle(x0, y0, x0+P-1, y0+P//3, fill=DARK, outline='')

        if happy:
            clamp_y = -3 if int(f * 0.2) % 2 == 0 else -2
            px(-4, clamp_y, DARK)
            px(3,  clamp_y, DARK)
            if self.happy_timer > 30:
                alpha = (self.happy_timer - 30) / 30
                hy = cy - 50 - int((1 - alpha) * 12)
                c.create_text(cx, hy, text='♥', fill='#FF6B9D',
                              font=('Arial', int(10 * alpha) + 5))

CrabPet()
