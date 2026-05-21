"""Chat window with glassmorphism, conversation sidebar, and streaming API."""
import tkinter as tk
from tkinter import ttk
import threading, urllib.request, json, queue, re

from config import load_cfg, save_cfg
from conversation_store import ConversationStore
from glass_effect import apply_acrylic


class ChatWindow(tk.Toplevel):
    # ── glassmorphism color palette ──────────────
    BG = '#F5F5FA'
    SIDEBAR_BG = '#EDEDF2'
    SIDEBAR_HOVER = '#E3E3EB'
    SIDEBAR_ACTIVE = '#DBDBE5'
    TOPBAR_BG = '#1C1C1E'
    USER_BG = '#EBF3FF'
    BOT_BG = '#F7F7F8'
    ACCENT = '#D97757'
    ACCENT_HOVER = '#C5684A'
    THINK_BG = '#FFF8E7'
    BORDER = '#E5E5EA'
    TEXT = '#1C1C1E'
    TEXT_SEC = '#888'

    def __init__(self, parent, store, on_reply=None):
        super().__init__(parent)
        self.store = store
        self.cfg = load_cfg()
        self.on_reply = on_reply
        self.busy = False
        self._q = queue.Queue()
        self._stream_txt = None
        self._think_visible = {}

        # load active conversation
        self.conv_id = store.get_active_id()
        conv = store.get(self.conv_id) if self.conv_id else None
        if not conv:
            self.conv_id = store.create(api_index=self.cfg.get('active_api', 0))
            conv = store.get(self.conv_id)
        self.messages = conv.get('messages', [])
        self.api_index = conv.get('api_index', self.cfg.get('active_api', 0))

        self.title("小钳")
        self.geometry("800x680")
        self.minsize(600, 450)
        self.configure(bg=self.BG)

        apply_acrylic(self)

        self._build()
        self._refresh_sidebar()
        self._replay_history()
        self._poll()
        self.entry.focus()

        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ── layout ───────────────────────────────────
    def _build(self):
        # main horizontal split
        main = tk.Frame(self, bg=self.BG)
        main.pack(fill='both', expand=True)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        # ── sidebar ──────────────────────────
        self._sidebar_frame = tk.Frame(main, bg=self.SIDEBAR_BG, width=210)
        self._sidebar_frame.grid(row=0, column=0, sticky='ns')
        self._sidebar_frame.pack_propagate(False)
        self._sidebar_frame.grid_propagate(False)

        sidebar_top = tk.Frame(self._sidebar_frame, bg=self.SIDEBAR_BG, padx=10, pady=10)
        sidebar_top.pack(fill='x')

        # new chat button
        new_btn = tk.Canvas(sidebar_top, width=170, height=32, bg=self.SIDEBAR_BG,
                            highlightthickness=0, cursor='hand2')
        new_btn.create_rounded_rect = lambda x1, y1, x2, y2, r, **kw: \
            new_btn.create_polygon(
                x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                x2, y2 - r, x2, y2, x2 - r, y2,
                x1 + r, y2, x1, y2, x1, y2 - r,
                x1, y1 + r, x1, y1, smooth=True, **kw)
        new_btn.create_rectangle(4, 2, 170, 32, fill=self.ACCENT, outline='')
        new_btn.create_text(87, 17, text='+ 新对话', fill='white',
                            font=('微软雅黑', 10))
        new_btn.pack(fill='x')
        self._bind_hover(new_btn, self.ACCENT, self.ACCENT_HOVER)
        new_btn.bind('<Button-1>', self._new_chat)

        # sidebar separator
        tk.Frame(self._sidebar_frame, bg=self.BORDER, height=1).pack(fill='x')

        # conversation list (canvas + scrollbar)
        self._list_frame = tk.Frame(self._sidebar_frame, bg=self.SIDEBAR_BG)
        self._list_frame.pack(fill='both', expand=True)

        self._list_canvas = tk.Canvas(self._list_frame, bg=self.SIDEBAR_BG,
                                      highlightthickness=0, width=210)
        list_sb = ttk.Scrollbar(self._list_frame, orient='vertical',
                                command=self._list_canvas.yview)
        self._list_canvas.configure(yscrollcommand=list_sb.set)
        list_sb.pack(side='right', fill='y')
        self._list_canvas.pack(side='left', fill='both', expand=True)

        self._list_inner = tk.Frame(self._list_canvas, bg=self.SIDEBAR_BG)
        self._list_win = self._list_canvas.create_window((0, 0), window=self._list_inner,
                                                         anchor='nw')
        self._list_inner.bind('<Configure>',
                              lambda e: self._list_canvas.configure(
                                  scrollregion=self._list_canvas.bbox('all')))
        self._list_canvas.bind('<Configure>',
                               lambda e: self._list_canvas.itemconfig(
                                   self._list_win, width=e.width))
        self._list_canvas.bind_all('<MouseWheel>', self._on_list_mousewheel)

        # ── right side ───────────────────────
        right = tk.Frame(main, bg=self.BG)
        right.grid(row=0, column=1, sticky='nsew')
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # top bar
        topbar = tk.Frame(right, bg=self.TOPBAR_BG, pady=8)
        topbar.grid(row=0, column=0, sticky='ew')

        tk.Label(topbar, text='✨  小钳', font=('微软雅黑', 12, 'bold'),
                 bg=self.TOPBAR_BG, fg='white').pack(side='left', padx=14)

        api_frame = tk.Frame(topbar, bg=self.TOPBAR_BG)
        api_frame.pack(side='right', padx=10)
        self._api_var = tk.StringVar()
        names = [a.get('name', f'API {i + 1}') for i, a in enumerate(self.cfg['apis'])]
        cb = ttk.Combobox(api_frame, textvariable=self._api_var, values=names,
                          width=14, state='readonly', font=('微软雅黑', 9))
        cb.pack(side='right')
        cb.set(names[self.api_index] if self.api_index < len(names) else names[0])
        cb.bind('<<ComboboxSelected>>', self._switch_api)

        # message area
        outer = tk.Frame(right, bg=self.BG)
        outer.grid(row=1, column=0, sticky='nsew')
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky='ns')
        self._canvas.grid(row=0, column=0, sticky='nsew')

        self._msg_frame = tk.Frame(self._canvas, bg=self.BG)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._msg_frame,
                                                      anchor='nw')
        self._msg_frame.bind('<Configure>', self._on_frame_resize)
        self._canvas.bind('<Configure>', self._on_canvas_resize)
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # separator
        tk.Frame(right, bg=self.BORDER, height=1).grid(row=2, column=0, sticky='ew')

        # input area
        bottom = tk.Frame(right, bg='#F2F2F7', pady=10)
        bottom.grid(row=3, column=0, sticky='ew', padx=12)

        input_wrap = tk.Frame(bottom, bg='white', relief='solid', bd=1)
        input_wrap.pack(fill='x')

        self.entry = tk.Text(input_wrap, font=('微软雅黑', 11), relief='flat', bd=0,
                             bg='white', height=3, wrap=tk.WORD, padx=10, pady=8)
        self.entry.pack(fill='x', expand=True)
        self._placeholder_text = '给 小钳 发消息...'
        self._set_placeholder()
        self.entry.bind('<FocusIn>', self._clear_placeholder)
        self.entry.bind('<FocusOut>', self._set_placeholder)
        self.entry.bind('<Return>', self._on_enter)

        toolbar = tk.Frame(input_wrap, bg='white', pady=4)
        toolbar.pack(fill='x', padx=8)

        tk.Button(toolbar, text='清空对话', font=('微软雅黑', 9), bg='white', fg='#888',
                  relief='flat', bd=0, cursor='hand2',
                  command=self._clear).pack(side='left', padx=8)

        self.send_btn = tk.Canvas(toolbar, width=32, height=32, bg='white',
                                  highlightthickness=0, cursor='hand2')
        self.send_btn.pack(side='right')
        self._draw_send_btn(active=True)
        self.send_btn.bind('<Button-1>', lambda e: self._send())

    # ── sidebar helpers ─────────────────────────
    def _on_list_mousewheel(self, e):
        if e.widget == self._list_canvas or self._is_child_of(e.widget, self._list_canvas):
            self._list_canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')

    def _is_child_of(self, widget, parent):
        w = widget
        while w is not None:
            if w == parent:
                return True
            w = w.master if hasattr(w, 'master') else None
        return False

    def _refresh_sidebar(self):
        for w in self._list_inner.winfo_children():
            w.destroy()

        convs = self.store.list_all()
        for conv in convs:
            self._add_sidebar_item(conv)

    def _add_sidebar_item(self, conv):
        is_active = conv['id'] == self.conv_id
        bg = self.SIDEBAR_ACTIVE if is_active else self.SIDEBAR_BG

        item = tk.Frame(self._list_inner, bg=bg, pady=4, padx=10, cursor='hand2')
        item.pack(fill='x')
        item.conv_id = conv['id']

        title = conv.get('title', '') or '(新对话)'
        tk.Label(item, text=title[:28], font=('微软雅黑', 10, 'bold' if is_active else 'normal'),
                 bg=bg, fg=self.TEXT, anchor='w').pack(fill='x')
        date = conv.get('updated_at', '')[:10]
        tk.Label(item, text=date, font=('微软雅黑', 8), bg=bg, fg=self.TEXT_SEC,
                 anchor='w').pack(fill='x')

        # hover effect
        def on_enter(e, f=item, c=conv):
            if c['id'] != self.conv_id:
                f.configure(bg=self.SIDEBAR_HOVER)
                for child in f.winfo_children():
                    child.configure(bg=self.SIDEBAR_HOVER)

        def on_leave(e, f=item, c=conv):
            if c['id'] != self.conv_id:
                f.configure(bg=self.SIDEBAR_BG)
                for child in f.winfo_children():
                    child.configure(bg=self.SIDEBAR_BG)

        def on_click(e, cid=conv['id']):
            if cid != self.conv_id and not self.busy:
                self._switch_to(cid)

        for child in item.winfo_children():
            child.bind('<Enter>', on_enter)
            child.bind('<Leave>', on_leave)
            child.bind('<Button-1>', on_click)
        item.bind('<Enter>', on_enter)
        item.bind('<Leave>', on_leave)
        item.bind('<Button-1>', on_click)
        item.bind('<Button-3>', lambda e, cid=conv['id']: self._sidebar_menu(e, cid))

    def _sidebar_menu(self, event, conv_id):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label='重命名', command=lambda: self._rename_conv(conv_id))
        menu.add_command(label='删除', command=lambda: self._delete_conv(conv_id))
        menu.tk_popup(event.x_root, event.y_root)

    def _rename_conv(self, conv_id):
        dialog = tk.Toplevel(self)
        dialog.title('重命名')
        dialog.geometry('300x100')
        dialog.configure(bg=self.BG)
        apply_acrylic(dialog)

        tk.Label(dialog, text='新名称:', font=('微软雅黑', 10), bg=self.BG).pack(pady=8)
        entry = tk.Entry(dialog, font=('微软雅黑', 10), width=30)
        entry.pack(padx=10)
        entry.focus()
        entry.bind('<Return>', lambda e: (self.store.update(conv_id, self.store.get(conv_id)['messages'],
                                                             title=entry.get()),
                                          dialog.destroy(), self._refresh_sidebar()))
        tk.Button(dialog, text='确认', command=lambda: (
            self.store.update(conv_id, self.store.get(conv_id)['messages'],
                              title=entry.get()),
            dialog.destroy(), self._refresh_sidebar()),
                  font=('微软雅黑', 10), bg=self.ACCENT, fg='white',
                  relief='flat').pack(pady=4)

    def _delete_conv(self, conv_id):
        remaining = [c for c in self.store.list_all() if c['id'] != conv_id]
        if len(remaining) == 0:
            # keep at least one
            conv_id_new = self.store.create()
        else:
            self.store.delete(conv_id)
            conv_id_new = self.store.get_active_id()
            if not conv_id_new:
                conv_id_new = remaining[0]['id']
                self.store.set_active(conv_id_new)

        if conv_id == self.conv_id:
            self._switch_to(conv_id_new, save_current=False)
        self._refresh_sidebar()

    def _ensure_sidebar_unbind(self):
        pass  # bindings are per-item, garbage-collected with widgets

    # ── conversation switching ──────────────────
    def _new_chat(self, e=None):
        self._save_current()
        self.conv_id = self.store.create(api_index=self.api_index)
        self.messages = []
        self._clear_msg_area()
        self._refresh_sidebar()
        self.entry.focus()

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
            self.api_index = conv.get('api_index', self.cfg.get('active_api', 0))
            names = [a.get('name', f'API {i + 1}') for i, a in enumerate(self.cfg['apis'])]
            if self.api_index < len(names):
                self._api_var.set(names[self.api_index])
        else:
            self.messages = []
        self._clear_msg_area()
        self._replay_history()
        self._refresh_sidebar()

    def _save_current(self):
        if self.conv_id:
            title = self.store.auto_title(self.messages)
            self.store.update(self.conv_id, list(self.messages),
                              api_index=self.api_index, title=title)

    # ── send / stream ───────────────────────────
    def _send(self):
        text = self.entry.get('1.0', tk.END).strip()
        if not text or text == self._placeholder_text or self.busy:
            return
        self.entry.delete('1.0', tk.END)
        self._set_placeholder()

        self._add_bubble('user', text)
        self.messages.append({"role": "user", "content": text})
        self.busy = True
        self._draw_send_btn(active=False)

        if len(self.messages) == 1:
            # auto-title from first message
            title = text[:35] + ('...' if len(text) > 35 else '')
            self.store.update(self.conv_id, self.messages,
                              api_index=self.api_index, title=title)
            self._refresh_sidebar()

        self._stream_txt, _ = self._add_bubble('assistant', '')
        self._scroll_bottom()

        threading.Thread(target=self._stream_ask, daemon=True).start()

    def _stream_ask(self):
        api = self.cfg['apis'][self.api_index]
        if not api.get('url') or not api.get('key'):
            self._q.put(('token', '\n*挥钳* 请先在设置中配置 API URL 和 Key'))
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
            self._q.put(('token', f'\n*闪烁* 出错了：{e}'))
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
                    self._refresh_sidebar()
                    if self.on_reply:
                        self.on_reply(val)
        except queue.Empty:
            pass
        self.after(50, self._poll)

    # ── UI helpers ───────────────────────────────
    def _draw_send_btn(self, active=True):
        self.send_btn.delete('all')
        color = self.ACCENT if active else '#CCC'
        self.send_btn.create_oval(2, 2, 30, 30, fill=color, outline='')
        self.send_btn.create_polygon(16, 8, 10, 20, 16, 17, 22, 20, fill='white', outline='')

    def _bind_hover(self, widget, color, hover_color):
        widget.bind('<Enter>', lambda e: widget.itemconfig('all', fill=hover_color))
        widget.bind('<Leave>', lambda e: widget.itemconfig('all', fill=color))

    def _set_placeholder(self, e=None):
        if not self.entry.get('1.0', 'end-1c').strip():
            self.entry.delete('1.0', tk.END)
            self.entry.insert('1.0', self._placeholder_text)
            self.entry.config(fg='#AAAAAA')

    def _clear_placeholder(self, e=None):
        if self.entry.get('1.0', 'end-1c') == self._placeholder_text:
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
        if self.busy or self._is_child_of(e.widget, self._canvas):
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

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
            lbl = tk.Label(bubble, text=text, font=('微软雅黑', 10),
                           bg=self.USER_BG, fg=self.TEXT, wraplength=380, justify='left')
            lbl.pack(anchor='w')
            return None, None

        # AI bubble
        row = tk.Frame(outer, bg=self.BG)
        row.pack(fill='x')
        tk.Label(row, text='✨', font=('Arial', 16), bg=self.BG).pack(side='left', anchor='n', padx=(0, 8))

        right = tk.Frame(row, bg=self.BG)
        right.pack(side='left', fill='x', expand=True)
        tk.Label(right, text='小钳', font=('微软雅黑', 9, 'bold'),
                 bg=self.BG, fg=self.TEXT_SEC).pack(anchor='w')

        if thinking:
            think_toggle = tk.Frame(right, bg=self.BG)
            think_toggle.pack(anchor='w', pady=(2, 0))
            self._think_visible[id(think_toggle)] = False
            think_body = tk.Frame(right, bg=self.THINK_BG, padx=10, pady=6)
            tk.Label(think_body, text=thinking, font=('微软雅黑', 9), fg=self.TEXT_SEC,
                     bg=self.THINK_BG, wraplength=380, justify='left').pack(anchor='w')

            def toggle(tb=think_body, tt=think_toggle, key=id(think_toggle)):
                self._think_visible[key] = not self._think_visible[key]
                if self._think_visible[key]:
                    tb.pack(anchor='w', fill='x', pady=(0, 4))
                    for w in tt.winfo_children():
                        w.destroy()
                    tk.Label(tt, text='▼ 思考过程', font=('微软雅黑', 9), fg=self.ACCENT,
                             bg=self.BG, cursor='hand2').pack(side='left')
                else:
                    tb.pack_forget()
                    for w in tt.winfo_children():
                        w.destroy()
                    tk.Label(tt, text='▶ 思考过程', font=('微软雅黑', 9), fg=self.ACCENT,
                             bg=self.BG, cursor='hand2').pack(side='left')
                self._scroll_bottom()

            tk.Label(think_toggle, text='▶ 思考过程', font=('微软雅黑', 9), fg=self.ACCENT,
                     bg=self.BG, cursor='hand2').pack(side='left')
            think_toggle.bind('<Button-1>', lambda e: toggle())
            for w in think_toggle.winfo_children():
                w.bind('<Button-1>', lambda e: toggle())

        bubble = tk.Frame(right, bg=self.BOT_BG, padx=14, pady=10)
        bubble.pack(anchor='w', fill='x')
        txt = tk.Text(bubble, font=('微软雅黑', 10), bg=self.BOT_BG, fg=self.TEXT,
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

    def _on_close(self):
        self._save_current()
        self.destroy()
