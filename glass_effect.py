import ctypes, ctypes.wintypes, platform


def _get_hwnd(toplevel):
    """Extract HWND from a tkinter Toplevel."""
    import tkinter as tk
    toplevel.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(toplevel.winfo_id())
    return hwnd


def apply_acrylic(toplevel):
    """Apply Windows 10+ acrylic blur behind to a Toplevel window.
    Falls back to set -alpha if acrylic is unsupported.
    """
    if not _try_dwm_accent(toplevel, accent_state=3):
        toplevel.attributes('-alpha', 0.92)


def _try_dwm_accent(toplevel, accent_state=3):
    """Try to enable DWM window composition accent.
    accent_state: 3=acrylic, 2=blurbehind
    Returns True on success.
    """
    if platform.release() < '10':
        return False

    hwnd = _get_hwnd(toplevel)

    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_uint),
            ("AccentFlags", ctypes.c_uint),
            ("GradientColor", ctypes.c_uint),
            ("AnimationId", ctypes.c_uint),
        ]

    class WINCOMPATTRDATA(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ACCENT_POLICY)),
            ("SizeOfData", ctypes.c_size_t),
        ]

    # SetWindowCompositionAttribute
    set_window_composition = ctypes.windll.user32.SetWindowCompositionAttribute
    set_window_composition.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(WINCOMPATTRDATA)]
    set_window_composition.restype = ctypes.c_bool

    accent = ACCENT_POLICY()
    accent.AccentState = accent_state
    accent.AccentFlags = 2  # draw all borders
    accent.GradientColor = 0x40F5F5FA  # ABGR: ~25% opaque light gray

    data = WINCOMPATTRDATA()
    data.Attribute = 19  # WCA_ACCENT_POLICY
    data.Data = ctypes.pointer(accent)
    data.SizeOfData = ctypes.sizeof(accent)

    return set_window_composition(hwnd, ctypes.pointer(data))
