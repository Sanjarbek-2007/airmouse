"""Minimal X11 (XWayland) helper: mark a window sticky + always-on-top via EWMH client messages.
Uses only ctypes + libX11, so there is no extra dependency."""
import ctypes
import ctypes.util


class _XClientMessage(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                ("format", ctypes.c_int), ("data", ctypes.c_long * 5)]


class _XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("xclient", _XClientMessage), ("pad", ctypes.c_long * 24)]


def make_sticky_above(win_id: int) -> bool:
    lib = ctypes.util.find_library("X11")
    if not lib:
        return False
    x = ctypes.CDLL(lib)
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XInternAtom.restype = ctypes.c_ulong
    x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x.XDefaultRootWindow.restype = ctypes.c_ulong
    x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
    x.XFlush.argtypes = [ctypes.c_void_p]
    dpy = x.XOpenDisplay(None)
    if not dpy:
        return False
    atom = lambda n: x.XInternAtom(dpy, n, 0)
    root = x.XDefaultRootWindow(dpy)
    state, sticky, above, skip = (atom(b"_NET_WM_STATE"), atom(b"_NET_WM_STATE_STICKY"),
                                  atom(b"_NET_WM_STATE_ABOVE"), atom(b"_NET_WM_STATE_SKIP_TASKBAR"))
    for prop in (sticky, above, skip):
        ev = _XEvent()
        ev.xclient.type = 33  # ClientMessage
        ev.xclient.window = win_id
        ev.xclient.message_type = state
        ev.xclient.format = 32
        ev.xclient.data[0] = 1  # _NET_WM_STATE_ADD
        ev.xclient.data[1] = prop
        ev.xclient.data[3] = 1  # source: normal application
        # SubstructureRedirectMask | SubstructureNotifyMask
        x.XSendEvent(dpy, root, 0, (1 << 20) | (1 << 19), ctypes.byref(ev))
    # also ask for all desktops directly
    x.XFlush(dpy)
    x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x.XCloseDisplay(dpy)
    return True
