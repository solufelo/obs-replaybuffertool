import os
import sys
import json
import ctypes
import asyncio
import threading
from ctypes import wintypes
from pathlib import Path
from aiohttp import web

# Win32 Constants
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A

HC_ACTION = 0

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('pt', wintypes.POINT),
        ('mouseData', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_void_p)
    ]

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_void_p)
    ]

# Virtual Key Mappings to HUD Elements
VK_MAP = {
    0x57: "W",
    0x41: "A",
    0x53: "S",
    0x44: "D",
    0x51: "Q",         # Tactical
    0x45: "INTERACT",  # Default Interact 'E'
    0x43: "CROUCH",    # 'C'
    0x11: "CROUCH",    # Left/Right Ctrl
    0x20: "JUMP",      # Space
    0x10: "SPRINT",    # Shift
    0x31: "WEAPON",    # 1
    0x32: "WEAPON",    # 2
    0x33: "WEAPON",    # 3 (Holster)
}

OVERLAY_DIR = Path(__file__).resolve().parent.parent / "overlay"
HTML_FILE = OVERLAY_DIR / "index.html"

connected_clients = set()
event_loop = None

def broadcast_event(data):
    if not connected_clients or not event_loop or event_loop.is_closed():
        return
    msg = json.dumps(data)
    for ws in list(connected_clients):
        if not ws.closed:
            asyncio.run_coroutine_threadsafe(ws.send_str(msg), event_loop)

# Low-level Keyboard Hook
def low_level_kbd_proc(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        is_down = (wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN)
        is_up = (wParam == WM_KEYUP or wParam == WM_SYSKEYUP)
        if is_down or is_up:
            kbd = KBDLLHOOKSTRUCT.from_address(lParam)
            vk = kbd.vkCode
            if vk in VK_MAP:
                name = VK_MAP[vk]
                broadcast_event({"type": "key", "name": name, "down": is_down})
                if name == "Q":
                    broadcast_event({"type": "key", "name": "TACTICAL", "down": is_down})
    return user32.CallNextHookEx(None, nCode, wParam, lParam)

# Low-level Mouse Hook (Ultra-low latency: skips mouse movements in < 1 microsecond)
def low_level_mouse_proc(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        # Zero-Lag Bypass for high-polling gaming mice
        if wParam == WM_MOUSEMOVE:
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        if wParam == WM_LBUTTONDOWN:
            broadcast_event({"type": "key", "name": "LMB", "down": True})
        elif wParam == WM_LBUTTONUP:
            broadcast_event({"type": "key", "name": "LMB", "down": False})
        elif wParam == WM_RBUTTONDOWN:
            broadcast_event({"type": "key", "name": "RMB", "down": True})
        elif wParam == WM_RBUTTONUP:
            broadcast_event({"type": "key", "name": "RMB", "down": False})
        elif wParam == WM_MOUSEWHEEL:
            ms = MSLLHOOKSTRUCT.from_address(lParam)
            # High word of mouseData contains delta (+120 for up, -120 for down)
            delta = ctypes.c_short(ms.mouseData >> 16).value
            if delta > 0:
                broadcast_event({"type": "wheel", "dir": "up"})
            elif delta < 0:
                broadcast_event({"type": "wheel", "dir": "down"})

    return user32.CallNextHookEx(None, nCode, wParam, lParam)

# HTTP / WebSocket Handlers
async def index_handler(request):
    if HTML_FILE.exists():
        return web.FileResponse(HTML_FILE)
    return web.Response(text="Overlay HTML file not found", status=404)

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)
    try:
        async for msg in ws:
            pass
    finally:
        connected_clients.discard(ws)
    return ws

def run_http_server():
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handler)
    runner = web.AppRunner(app)
    event_loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '127.0.0.1', 8998)
    event_loop.run_until_complete(site.start())
    event_loop.run_forever()

def main():
    # Start Web / WebSocket Server in background thread
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()

    # Install Windows Global Hooks
    kbd_callback = HOOKPROC(low_level_kbd_proc)
    mouse_callback = HOOKPROC(low_level_mouse_proc)

    kbd_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kbd_callback, 0, 0)
    mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_callback, 0, 0)

    if not kbd_hook or not mouse_hook:
        print(f"[InputOverlay] Failed to register hooks. Kbd: {bool(kbd_hook)}, Mouse: {bool(mouse_hook)}")
        sys.exit(1)

    print("[InputOverlay] Global input hooks registered. Server live at http://127.0.0.1:8998", flush=True)

    # Win32 Message Pump (Required for SetWindowsHookEx)
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if kbd_hook:
            user32.UnhookWindowsHookEx(kbd_hook)
        if mouse_hook:
            user32.UnhookWindowsHookEx(mouse_hook)

if __name__ == "__main__":
    main()
