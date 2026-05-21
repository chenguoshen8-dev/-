"""Clean glassmorphism chat window with conversation management."""
import tkinter as tk
from tkinter import ttk
import threading, urllib.request, json, queue, re

from config import load_cfg, save_cfg
from conversation_store import ConversationStore
from glass_effect import apply_acrylic


class ChatWindow(tk.Toplevel):
    FONT = ('Microsoft YaHei UI', 10)
    FONT_BOLD = ('Microsoft YaHei UI', 10, 'bold')
    FONT_SM = ('Microsoft YaHei UI', 9)
    FONT_TITLE = ('Microsoft YaHei UI', 12, 'bold')
    FONT_INPUT = ('Microsoft YaHei UI', 11)
    BG = '#F5F5FA'
    TOPBAR_BG = '#1C1C1E'
    USER_BG = '#EBF3FF'
    BOT_BG = '#F7F7F8'
    ACCENT = '#D97757'
    THINK_BG = '#FFF8E7'
    BORDER = '#E5E5EA'
    TEXT = '#111111'
    TEXT_SEC = '#666666'

    def __init__(self, parent, store, on_reply=None):
        super().__init__(parent)
        self.parent = parent
        self.store = store
        self.on_reply = on_reply
        self.busy = False
        self._dead = False
        self._q = queue.Queue()
        self._stream_txt = None
        self._think_visible = {}

        self._load_session()
        self.cfg = load_cfg()

        self.title("小钳")
        self.geometry("600x680")
        self.minsize(420, 440)
        self.configure(bg=self.BG)

        apply_acrylic(self)

        self._build()
        self._replay_history()
        self._poll()
        self.entry.focus()

        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _load_session(self):
        self.conv_id = self.store.get_active_id()
        conv = self.store.get(self.conv_id) if self.conv_id else None
        if not conv:
            self.conv_id = self.store.create(api_index=0)
            conv = self.store.get(self.conv_id)
        self.messages = conv.get('messages', [])
        self.api_index = conv.get('api_index', 0)

    # ── layout ───────────────────────────────────
    def _build(self):
        # top bar
        topbar = tk.Frame(self, bg=self.TOPBAR_BG, pady=8)
        topbar.pack(fill='x')

        tk.Label(topbar, text='✨  小钳', font=self.FONT_TITLE,
                 bg=self.TOPBAR_BG, fg='white').pack(side='left', padx=14)

        # right side controls
        ctrls = tk.Frame(topbar, bg=self.TOPBAR_BG)
        ctrls.pack(side='right', padx=8)

        # conversation picker
        self._conv_var = tk.StringVar()
        self._conv_cb = ttk.Combobox(ctrls, textvariable=self._conv_var,
                                     width=16, state='readonly', font=self.FONT_SM)
        self._conv_cb.pack(side='left', padx=2)
        self._conv_cb.bind('<<ComboboxSelected>>', self._on_conv_select)
        self._refresh_conv_list()

        # new chat button
        tk.Button(ctrls, text='+', font=('Arial', 13), bg=self.TOPBAR_BG, fg='white',
                  relief='flat', bd=0, cursor='hand2', padx=4,
                  command=self._new_chat).pack(side='left', padx=2)

        # manage conversations button
        tk.Button(ctrls, text='...', font=('Arial', 11), bg=self.TOPBAR_BG, fg='white',
                  relief='flat', bd=0, cursor='hand2', padx=4,
                  command=self._manage_convs).pack(side='left', padx=2)

        # API picker
        self._api_var = tk.StringVar()
        names = [a.get('name', f'API {i + 1}') for i, a in enumerate(self.cfg['apis'])]
        api_cb = ttk.Combobox(ctrls, textvariable=self._api_var, values=names,
                              width=12, state='readonly', font=self.FONT_SM)
        api_cb.pack(side='left', padx=4)
        api_cb.set(names[self.api_index] if self.api_index < len(names) else names[0])
        api_cb.bind('<<ComboboxSelected>>', self._switch_api)

        # message area
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

        # separator
        tk.Frame(self, bg=self.BORDER, height=1).pack(fill='x')

        # input area
        bottom = tk.Frame(self, bg='#F2F2F7', pady=10)
        bottom.pack(fill='x', padx=12)

        input_wrap = tk.Frame(bottom, bg='white', relief='solid', bd=1)
        input_wrap.pack(fill='x')

        self.entry = tk.Text(input_wrap, font=self.FONT_INPUT, relief='flat', bd=0,
                             bg='white', height=3, wrap=tk.WORD, padx=10, pady=8)
        self.entry.pack(fill='x', expand=True)
        self._ph = '给 小钳 发消息...'
        self._set_placeholder()
        self.entry.bind('<FocusIn>', self._clear_placeholder)
        self.entry.bind('<FocusOut>', self._set_placeholder)
        self.entry.bind('<Return>', self._on_enter)

        toolbar = tk.Frame(input_wrap, bg='white', pady=4)
        toolbar.pack(fill='x', padx=8)

        tk.Button(toolbar, text='清空对话', font=self.FONT_SM, bg='white', fg='#888',
                  relief='flat', bd=0, cursor='hand2',
                  command=self._clear).pack(side='left')

        self.send_btn = tk.Canvas(toolbar, width=32, height=32, bg='white',
                                  highlightthickness=0, cursor='hand2')
        self.send_btn.pack(side='right')
        self._draw_send_btn(active=True)
        self.send_btn.bind('<Button-1>', lambda e: self._send())

        # scroll bindings
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    # ── conversation management ───────────────────
    def _refresh_conv_list(self):
        convs = self.store.list_all()
        names = []
        for c in convs:
            t = c.get('title') or '(新对话)'
            names.append(t[:25])
        self._conv_cb['values'] = names
        # select current
        for i, c in enumerate(convs):
            if c['id'] == self.conv_id:
                self._conv_var.set(names[i] if i < len(names) else '')
                return
        if names:
            self._conv_var.set(names[0])

    def _on_conv_select(self, e=None):
        sel = self._conv_cb.current()
        convs = self.store.list_all()
        if sel >= 0 and sel < len(convs):
            self._switch_to(convs[sel]['id'])

    def _new_chat(self, e=None):
        if self.busy:
            return
        self._save_current()
        self.conv_id = self.store.create(api_index=self.api_index)
        self.messages = []
        self._clear_msg_area()
        self._refresh_conv_list()
        self.entry.focus()

    def _manage_convs(self):
        menu = tk.Menu(self, tearoff=0)
        convs = self.store.list_all()
        for i, c in enumerate(convs):
            if c['id'] == self.conv_id:
                t = (c.get('title') or '(新对话)')[:25]
                menu.add_command(label=f'✎ 重命名「{t}」', command=lambda cid=c['id']: self._rename_conv(cid))
                menu.add_command(label=f'✕ 删除「{t}」', command=lambda cid=c['id']: self._delete_conv(cid))
                break
        # show below the ... button
        x = self.winfo_x() + self.winfo_width() - 60
        y = self.winfo_y() + 40
        menu.tk_popup(x, y)

    def _rename_conv(self, conv_id):
        d = tk.Toplevel(self)
        d.title('重命名')
        d.geometry('280x100')
        d.configure(bg=self.BG)
        apply_acrylic(d)
        tk.Label(d, text='新名称:', font=self.FONT, bg=self.BG).pack(pady=8)
        e = tk.Entry(d, font=self.FONT, width=28)
        e.pack(padx=10)
        e.focus()
        e.bind('<Return>', lambda ev: self._do_rename(conv_id, e.get(), d))
        tk.Button(d, text='确认', command=lambda: self._do_rename(conv_id, e.get(), d),
                  font=self.FONT, bg=self.ACCENT, fg='white', relief='flat').pack(pady=4)

    def _do_rename(self, conv_id, new_title, dialog):
        conv = self.store.get(conv_id)
        if conv:
            self.store.update(conv_id, conv['messages'], api_index=conv.get('api_index', 0), title=new_title)
        self._refresh_conv_list()
        dialog.destroy()

    def _delete_conv(self, conv_id):
        remaining = [c for c in self.store.list_all() if c['id'] != conv_id]
        if not remaining:
            new_id = self.store.create()
        else:
            self.store.delete(conv_id)
            new_id = self.store.get_active_id()
            if not new_id:
                new_id = remaining[0]['id']
                self.store.set_active(new_id)
        if conv_id == self.conv_id:
            self._switch_to(new_id, save_current=False)
        self._refresh_conv_list()

    def _switch_to(self, conv_id, save_current=True):
        if self.busy:
            return
        if save_current:
            self._save_current()
        self.conv_id = conv_id
        self.store.set_active(conv_id)
        conv = self.store.get(conv_id)
        if conv:
            self.messages = conv.get('messages', [])
            self.api_index = conv.get('api_index', 0)
            names = [a.get('name', f'API {i + 1}') for i, a in enumerate(self.cfg['apis'])]
            if self.api_index < len(names):
                self._api_var.set(names[self.api_index])
        else:
            self.messages = []
        self._clear_msg_area()
        self._replay_history()
        self._refresh_conv_list()

    def _save_current(self):
        if self.conv_id:
            title = self.store.auto_title(self.messages)
            self.store.update(self.conv_id, list(self.messages), api_index=self.api_index, title=title)

    # ── send / stream ───────────────────────────
    def _send(self):
        text = self.entry.get('1.0', tk.END).strip()
        if not text or text == self._ph or self.busy:
            return
        self.entry.delete('1.0', tk.END)
        self._set_placeholder()

        self._add_bubble('user', text)
        self.messages.append({"role": "user", "content": text})
        self.busy = True
        self._draw_send_btn(active=False)

        if len(self.messages) == 1:
            title = text[:35] + ('...' if len(text) > 35 else '')
            self.store.update(self.conv_id, self.messages, api_index=self.api_index, title=title)
            self._refresh_conv_list()

        # reload config in case settings changed
        self.cfg = load_cfg()

        self._stream_txt, _ = self._add_bubble('assistant', '')
        self._scroll_bottom()
        threading.Thread(target=self._stream_ask, daemon=True).start()

    def _stream_ask(self):
        api = self.cfg['apis'][self.api_index]
        if not api.get('url') or not api.get('key'):
            self._q.put(('token', '\n请先在设置中配置 API URL 和 Key'))
            self._q.put(('done', ''))
            return

        system = "你是一只可爱的Claude星星桌宠，名叫「小钳」，说话简短可爱，偶尔用星星闪烁的动作描述自己。"
        msgs = [{"role": "system", "content": system}] + self.messages

        data = json.dumps({"model": api.get('model', 'claude-opus-4-7'),
                           "messages": msgs, "max_tokens": 800,
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
                    except Exception:
                        pass
        except Exception as e:
            self._q.put(('token', f'\n出错了：{e}'))
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
                    self.messages.append({"role": "assistant", "content": val})
                    self._save_current()
                    self.busy = False
                    self._draw_send_btn(active=True)
                    self._refresh_conv_list()
                    if self.on_reply:
                        self.on_reply(val)
        except queue.Empty:
            pass
        if not self._dead:
            try:
                self.after(50, self._poll)
            except tk.TclError:
                pass

    # ── API switching ──────────────────────────
    def _switch_api(self, e=None):
        name = self._api_var.get()
        for i, a in enumerate(self.cfg['apis']):
            if a['name'] == name:
                self.api_index = i
                self.store.update(self.conv_id, self.messages, api_index=i)
                return

    # ── message bubbles ──────────────────────────
    def _add_bubble(self, role, text='', thinking=''):
        is_user = role == 'user'
        outer = tk.Frame(self._msg_frame, bg=self.BG, pady=4)
        outer.pack(fill='x', padx=16)

        if is_user:
            bubble = tk.Frame(outer, bg=self.USER_BG, padx=14, pady=10)
            bubble.pack(anchor='e')
            tk.Label(bubble, text=text, font=self.FONT,
                     bg=self.USER_BG, fg=self.TEXT, wraplength=380, justify='left').pack(anchor='w')
            return None, None

        row = tk.Frame(outer, bg=self.BG)
        row.pack(fill='x')
        tk.Label(row, text='✨', font=('Arial', 16), bg=self.BG).pack(side='left', anchor='n', padx=(0, 8))

        right = tk.Frame(row, bg=self.BG)
        right.pack(side='left', fill='x', expand=True)
        tk.Label(right, text='小钳', font=self.FONT_BOLD,
                 bg=self.BG, fg=self.TEXT_SEC).pack(anchor='w')

        if thinking:
            self._build_thinking_toggle(right, thinking)

        bubble = tk.Frame(right, bg=self.BOT_BG, padx=14, pady=10)
        bubble.pack(anchor='w', fill='x')
        txt = tk.Text(bubble, font=self.FONT, bg=self.BOT_BG, fg=self.TEXT,
                      relief='flat', bd=0, wrap=tk.WORD, height=1, cursor='arrow')
        txt.pack(fill='x')
        txt.tag_config('bold', font=('微软雅黑', 10, 'bold'))
        txt.tag_config('code', font=('Consolas', 9), background='#EFEFEF', foreground='#C7254E')
        if text:
            self._insert_rich(txt, text)
            txt.config(state='disabled')
            self._auto_height(txt)
        return txt, bubble

    def _build_thinking_toggle(self, parent, thinking):
        toggle = tk.Frame(parent, bg=self.BG)
        toggle.pack(anchor='w', pady=(2, 0))
        body = tk.Frame(parent, bg=self.THINK_BG, padx=10, pady=6)
        tk.Label(body, text=thinking, font=self.FONT_SM, fg=self.TEXT_SEC,
                 bg=self.THINK_BG, wraplength=380, justify='left').pack(anchor='w')

        key = id(toggle)
        self._think_visible[key] = False

        def toggle_fn():
            self._think_visible[key] = not self._think_visible[key]
            if self._think_visible[key]:
                body.pack(anchor='w', fill='x', pady=(0, 4))
                for w in toggle.winfo_children():
                    w.destroy()
                tk.Label(toggle, text='▼ 思考过程', font=self.FONT_SM, fg=self.ACCENT,
                         bg=self.BG, cursor='hand2').pack(side='left')
            else:
                body.pack_forget()
                for w in toggle.winfo_children():
                    w.destroy()
                tk.Label(toggle, text='▶ 思考过程', font=self.FONT_SM, fg=self.ACCENT,
                         bg=self.BG, cursor='hand2').pack(side='left')
            self._scroll_bottom()

        tk.Label(toggle, text='▶ 思考过程', font=self.FONT_SM, fg=self.ACCENT,
                 bg=self.BG, cursor='hand2').pack(side='left')
        toggle.bind('<Button-1>', lambda e: toggle_fn())
        for w in toggle.winfo_children():
            w.bind('<Button-1>', lambda e: toggle_fn())

    def _insert_rich(self, txt, text):
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

    def _replay_history(self):
        for msg in self.messages:
            self._add_bubble(msg['role'], msg['content'])
        self._scroll_bottom()

    def _clear_msg_area(self):
        for w in self._msg_frame.winfo_children():
            w.destroy()

    def _clear(self):
        self._clear_msg_area()
        self.messages.clear()
        self._save_current()
        self._scroll_bottom()

    # ── UI helpers ─────────────────────────────
    def _draw_send_btn(self, active=True):
        self.send_btn.delete('all')
        color = self.ACCENT if active else '#CCC'
        self.send_btn.create_oval(2, 2, 30, 30, fill=color, outline='')
        self.send_btn.create_polygon(16, 8, 10, 20, 16, 17, 22, 20, fill='white', outline='')

    def _set_placeholder(self, e=None):
        if not self.entry.get('1.0', 'end-1c').strip():
            self.entry.delete('1.0', tk.END)
            self.entry.insert('1.0', self._ph)
            self.entry.config(fg='#AAAAAA')

    def _clear_placeholder(self, e=None):
        if self.entry.get('1.0', 'end-1c') == self._ph:
            self.entry.delete('1.0', tk.END)
            self.entry.config(fg=self.TEXT)

    def _on_enter(self, e):
        if not (e.state & 0x1):
            self._send()
            return 'break'

    def _on_frame_resize(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def _on_canvas_resize(self, e):
        self._canvas.itemconfig(self._canvas_win, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    def _on_close(self):
        self._dead = True
        self._save_current()
        self.destroy()
