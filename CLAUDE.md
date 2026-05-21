# Claude Pet (小钳)

A pixel-art crab desktop pet for Windows, driven by Claude API.

## Project Structure
- `claude_pet.py` — Single-file application (684 lines), Python 3 + tkinter only
- `claude_pet_cfg.json` — Runtime config (auto-generated, gitignored — contains API keys)

## How to Run
```bash
python claude_pet.py
```
No external dependencies. Uses only stdlib (tkinter, urllib, json, threading, etc.).

## Architecture
Three classes in `claude_pet.py`:
- **CrabPet** (main) — Transparent always-on-top tkinter window, pixel-art crab, walk/idle/happy animations, drag-and-drop, right-click menu
- **ChatWindow** — Chat dialog with streaming API responses, markdown rendering, collapsible thinking display
- **SettingsWindow** — 4-tab config UI (API config ×3, pet size/topmost, system, about)

Config file stores up to 3 API endpoints with keys, pet size (2-6), and topmost toggle.

## Key Notes
- Singleton via Windows mutex (`Global\\ClaudeCrabPet_Singleton`)
- No package dependencies — pure stdlib
- API response streaming happens in a background thread, UI updates via `queue.Queue` polled by `after()`
- The `_draw()` method recreates all pixel rectangles every frame — this is the main perf bottleneck
