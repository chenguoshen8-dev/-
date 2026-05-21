"""Claude star/sparkle desktop pet pixel art."""

COL = '#D97757'      # warm amber body
LIGHT = '#F0A880'    # body highlight
DARK = '#A85535'     # shadow
EYE = '#1C1C1E'      # eyes
BLUSH = '#FFB3C1'    # blush
GOLD = '#F5A623'     # sparkle tips
MOUTH_COL = '#1C1C1E'

# ── pixel coordinate sets ──────────────────────────

STAR_BODY = [
    (-1, -2), (0, -2), (1, -2),
    (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1),
    (-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0),
    (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1),
    (-1, 2), (0, 2), (1, 2),
]

BODY_HIGHLIGHT = [
    (-1, -1), (0, -1),
    (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
]

BODY_DARK = [
    (-3, 0), (3, 0), (0, 2),
]

# Sparkle arms — four diagonals + top/bottom tips
SPARKLE_TL = [(-3, -2), (-4, -2), (-3, -3), (-4, -3)]
SPARKLE_TR = [(3, -2), (4, -2), (3, -3), (4, -3)]
SPARKLE_BL = [(-3, 2), (-4, 2), (-3, 3), (-4, 3)]
SPARKLE_BR = [(3, 2), (4, 2), (3, 3), (4, 3)]
SPARKLE_TOP = [(0, -3), (-1, -4), (0, -4), (1, -4)]
SPARKLE_BOT = [(0, 3), (-1, 4), (0, 4), (1, 4)]

SPARKLE_TL_TIP = [(-4, -3), (-5, -4)]
SPARKLE_TR_TIP = [(4, -3), (5, -4)]
SPARKLE_BL_TIP = [(-4, 3), (-5, 4)]
SPARKLE_BR_TIP = [(4, 3), (5, 4)]
SPARKLE_TOP_TIP = [(0, -5)]
SPARKLE_BOT_TIP = [(0, 5)]

# Walk animation: which arm pairs alternate
WALK_PHASE_0_ARMS = (SPARKLE_TL, SPARKLE_BR)
WALK_PHASE_1_ARMS = (SPARKLE_TR, SPARKLE_BL)

# Face
EYES = [(-2, -1), (1, -1)]
MOUTH_SMILE = [(-1, 1), (0, 1)]
MOUTH_HAPPY = [(-2, 1), (-1, 2), (0, 2), (1, 1)]
BLUSH_SPOTS = [(-4, 0), (4, 0)]


def draw_star(canvas, cx, cy, P, frame, state, blinking,
              happy_timer, bubble_text, bubble_timer):
    """Draw the Claude sparkle pet. Clears canvas first."""
    canvas.delete('all')

    # ── speech bubble ────────────────────────────
    if bubble_timer > 0 and bubble_text:
        bx, by = cx, cy - 55
        tw = min(len(bubble_text) * 7 + 20, 210)
        canvas.create_rectangle(bx - tw // 2, by - 15, bx + tw // 2, by + 15,
                                fill='white', outline='#CCC')
        canvas.create_polygon(cx - 5, by + 15, cx + 5, by + 15, cx, by + 23,
                              fill='white', outline='#CCC')
        canvas.create_text(bx, by, text=bubble_text, fill='#111',
                           font=('Microsoft YaHei UI', 8), width=tw - 10)

    happy = state == 'happy'
    phase = int(frame * 0.3) % 2 if state == 'walk' else 0
    idle_phase = int(frame * 0.05) % 2 if state == 'idle' else 0

    # ── sparkle arms (walk alternation) ──────────
    # idle — gentle pulse: half arms alternate
    if state == 'idle':
        active_arms = WALK_PHASE_0_ARMS if idle_phase == 0 else WALK_PHASE_1_ARMS
        inactive_arms = WALK_PHASE_1_ARMS if idle_phase == 0 else WALK_PHASE_0_ARMS
    elif happy:
        active_arms = (SPARKLE_TL, SPARKLE_TR, SPARKLE_BL, SPARKLE_BR, SPARKLE_TOP, SPARKLE_BOT)
        inactive_arms = ()
    else:
        active_arms = WALK_PHASE_0_ARMS if phase == 0 else WALK_PHASE_1_ARMS
        inactive_arms = WALK_PHASE_1_ARMS if phase == 0 else WALK_PHASE_0_ARMS

    # ── helper ───────────────────────────────────
    def px(gx, gy, color=COL):
        x0 = cx + gx * P
        y0 = cy + gy * P
        canvas.create_rectangle(x0, y0, x0 + P - 1, y0 + P - 1,
                                fill=color, outline='')

    # ── draw sparkle tips (gold) ─────────────────
    for arm in active_arms:
        for gx, gy in arm:
            px(gx, gy, GOLD)
    for arm in inactive_arms:
        for gx, gy in arm[:2]:  # only base pixels when retracted
            px(gx, gy, GOLD)

    if happy:
        for tip in [(SPARKLE_TL_TIP, SPARKLE_TR_TIP, SPARKLE_BL_TIP, SPARKLE_BR_TIP,
                      SPARKLE_TOP_TIP, SPARKLE_BOT_TIP)]:
            for group in tip:
                for gx, gy in group:
                    px(gx, gy, GOLD)
    elif state == 'idle' and idle_phase == 0:
        tips = SPARKLE_TL_TIP + SPARKLE_BR_TIP
        for gx, gy in tips:
            px(gx, gy, GOLD)
    elif state == 'idle':
        tips = SPARKLE_TR_TIP + SPARKLE_BL_TIP
        for gx, gy in tips:
            px(gx, gy, GOLD)
    elif state == 'walk':
        tips = SPARKLE_TL_TIP + SPARKLE_BR_TIP if phase == 0 else SPARKLE_TR_TIP + SPARKLE_BL_TIP
        for gx, gy in tips:
            px(gx, gy, GOLD)

    # ── top/bottom sparkles ─────────────────────
    if happy:
        for p in SPARKLE_TOP + SPARKLE_BOT:
            px(p[0], p[1], GOLD)
        for p in SPARKLE_TOP_TIP + SPARKLE_BOT_TIP:
            px(p[0], p[1], GOLD)
    elif state == 'idle':
        top_set = SPARKLE_TOP if idle_phase == 0 else SPARKLE_BOT
        for p in top_set:
            px(p[0], p[1], GOLD)
    else:
        top_set = SPARKLE_TOP if phase == 0 else SPARKLE_BOT
        for p in top_set:
            px(p[0], p[1], GOLD)

    # ── body shadow ──────────────────────────────
    for gx, gy in BODY_DARK:
        px(gx, gy, DARK)

    # ── main body ────────────────────────────────
    for gx, gy in STAR_BODY:
        px(gx, gy, COL)

    # ── body highlight ───────────────────────────
    for gx, gy in BODY_HIGHLIGHT:
        px(gx, gy, LIGHT)

    # ── face ─────────────────────────────────────
    # blush when happy
    if happy:
        for gx, gy in BLUSH_SPOTS:
            px(gx, gy, BLUSH)

    # eyes / blink
    for gx, gy in EYES:
        if not blinking:
            px(gx, gy, EYE)
        else:
            x0 = cx + gx * P
            y0 = cy + gy * P + P // 3
            canvas.create_rectangle(x0, y0, x0 + P - 1, y0 + P // 3,
                                    fill=DARK, outline='')

    # mouth
    mouth = MOUTH_HAPPY if happy else MOUTH_SMILE
    for gx, gy in mouth:
        px(gx, gy, MOUTH_COL)

    # ── happy effect ─────────────────────────────
    if happy and happy_timer > 30:
        alpha = (happy_timer - 30) / 30.0
        hy = cy - 50 - int((1 - alpha) * 12)
        canvas.create_text(cx, hy, text='♥', fill='#FF6B9D',
                           font=('Arial', int(10 * alpha) + 5))
