import tkinter as tk
import random, sys, os, ctypes

# singleton
_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\ClaudeStarPet_Singleton")
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

from config import load_cfg, save_cfg
from pet_drawing import draw_star
from conversation_store import ConversationStore
from chat_window import ChatWindow
from settings_window import SettingsWindow


class StarPet:
    def __init__(self):
        self.cfg = load_cfg()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.store = ConversationStore(base_dir)

        # migration: legacy history
        conv_id = self.store.get_active_id()
        if not conv_id or not self.store.get(conv_id):
            self.store.create(api_index=self.cfg.get('active_api', 0))

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', self.cfg['topmost'])
        self.root.attributes('-transparentcolor', '#010101')
        self.root.configure(bg='#010101')

        self.W, self.H = 130, 120
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H,
                                bg='#010101', highlightthickness=0)
        self.canvas.pack()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.x = float(sw - 180)
        self.y = float(sh - 160)

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
        self.menu.add_command(label='⚙ 设置', command=self._open_settings)
        self.menu.add_separator()
        self.menu.add_command(label='退出', command=self.root.destroy)

        self._chat_win = None
        self._settings_win = None
        self._update()
        self.root.mainloop()

    # ── interaction ──────────────────────────────
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
            self.bubble_text = text[:30] + ("..." if len(text) > 30 else "")
            self.bubble_timer = 200
            self._do_happy()

        self._chat_win = ChatWindow(self.root, self.store, on_reply)

    def _open_settings(self):
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus()
            return

        def on_save(new_cfg):
            self.cfg = new_cfg
            self.root.attributes('-topmost', new_cfg['topmost'])

        self._settings_win = SettingsWindow(self.root, self.cfg, on_save)

    # ── game loop ────────────────────────────────
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
                if self.x < 0:           self.x = 0;         self.vx = abs(self.vx)
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
        P = max(2, self.cfg.get('pet_size', 3))
        cx, cy = self.W // 2, self.H // 2 + 5

        draw_star(
            canvas=self.canvas,
            cx=cx, cy=cy, P=P,
            frame=self.frame,
            state=self.state,
            blinking=self.blinking,
            happy_timer=self.happy_timer,
            bubble_text=self.bubble_text,
            bubble_timer=self.bubble_timer,
        )


StarPet()
