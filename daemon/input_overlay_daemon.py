import os
import sys
import json
import time
import ctypes
import asyncio
import threading
from ctypes import wintypes
from pathlib import Path
from aiohttp import web

# Win32 Constants
WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
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

# Tracked Virtual Keys (0-Lag GetAsyncKeyState Polling)
VK_MAP = {
    0x57: "W",
    0x41: "A",
    0x53: "S",
    0x44: "D",
    0x51: "Q",         # Q (Ability / Gadget / Tactical)
    0x45: "E",         # E (Interact / Use)
    0x52: "R",         # R (Reload)
    0x46: "F",         # F (Melee / Gadget / Interact)
    0x47: "G",         # G (Grenade)
    0x56: "V",         # V (Melee)
    0x43: "C",         # C (Crouch / Slide)
    0x11: "CTRL",      # Ctrl (Crouch / Prone)
    0xA2: "CTRL",      # Left Ctrl
    0x20: "SPACE",     # Space (Jump / Vault)
    0x10: "SHIFT",     # Shift (Sprint / Zoom)
    0xA0: "SHIFT",     # Left Shift
    0x50: "P",         # P (Tactical)
    0x12: "ALT",       # Alt
    0xA4: "ALT",       # Left Alt
    0x31: "1",         # 1
    0x32: "2",         # 2
    0x33: "3",         # 3 (Holster)
    0x34: "4",         # 4 (Heal)
    0x35: "5",         # 5 (Gadget / Special)
    0x09: "TAB",       # Tab
    0x5A: "Z",         # Z
    0x58: "X",         # X
    0x42: "B",         # B
}

OVERLAY_DIR = Path(__file__).resolve().parent.parent / "overlay"
HTML_FILE = OVERLAY_DIR / "index.html"
JITTER_FILE = OVERLAY_DIR / "jitter_overlay.html"

connected_clients = set()
event_loop = None

def broadcast_event(data):
    if not connected_clients or not event_loop or event_loop.is_closed():
        return
    msg = json.dumps(data)
    for ws in list(connected_clients):
        if not ws.closed:
            try:
                asyncio.run_coroutine_threadsafe(ws.send_str(msg), event_loop)
            except Exception:
                pass

# Low-level Mouse Hook for 100% Reliable In-Game Mouse & Wheel Telemetry
def low_level_mouse_proc(nCode, wParam, lParam):
    if nCode == HC_ACTION and connected_clients:
        if wParam == WM_MOUSEMOVE:
            return user32.CallNextHookEx(None, nCode, wParam, lParam)
        if wParam == WM_MOUSEWHEEL:
            ms = MSLLHOOKSTRUCT.from_address(lParam)
            delta = ctypes.c_short(ms.mouseData >> 16).value
            if delta > 0:
                broadcast_event({"type": "wheel", "dir": "up"})
            elif delta < 0:
                broadcast_event({"type": "wheel", "dir": "down"})
        elif wParam == WM_LBUTTONDOWN:
            broadcast_event({"type": "key", "name": "LMB", "down": True})
        elif wParam == WM_LBUTTONUP:
            broadcast_event({"type": "key", "name": "LMB", "down": False})
        elif wParam == WM_RBUTTONDOWN:
            broadcast_event({"type": "key", "name": "RMB", "down": True})
        elif wParam == WM_RBUTTONUP:
            broadcast_event({"type": "key", "name": "RMB", "down": False})
        elif wParam == WM_XBUTTONDOWN:
            ms = MSLLHOOKSTRUCT.from_address(lParam)
            xbtn = ms.mouseData >> 16
            if xbtn == 1:
                broadcast_event({"type": "key", "name": "MB4", "down": True})
                broadcast_event({"type": "key", "name": "HOLSTER", "down": True})
            elif xbtn == 2:
                broadcast_event({"type": "key", "name": "MB5", "down": True})
                broadcast_event({"type": "key", "name": "HEAL", "down": True})
        elif wParam == WM_XBUTTONUP:
            ms = MSLLHOOKSTRUCT.from_address(lParam)
            xbtn = ms.mouseData >> 16
            if xbtn == 1:
                broadcast_event({"type": "key", "name": "MB4", "down": False})
                broadcast_event({"type": "key", "name": "HOLSTER", "down": False})
            elif xbtn == 2:
                broadcast_event({"type": "key", "name": "MB5", "down": False})
                broadcast_event({"type": "key", "name": "HEAL", "down": False})
    return user32.CallNextHookEx(None, nCode, wParam, lParam)

# Zero-Overhead Adaptive Poller: 120-240 Hz when active, sleeps when no clients connected
def poll_keys_thread():
    last_states = {name: False for name in set(VK_MAP.values())}

    while True:
        try:
            if not connected_clients:
                # Zero CPU when overlay is not being viewed
                time.sleep(0.20)
                continue

            current_states = {name: False for name in last_states}
            for vk, name in VK_MAP.items():
                if user32.GetAsyncKeyState(vk) & 0x8000:
                    current_states[name] = True

            for name, is_down in current_states.items():
                if is_down != last_states[name]:
                    broadcast_event({"type": "key", "name": name, "down": is_down})
                    last_states[name] = is_down

            time.sleep(0.005)  # ~200 Hz ultra-low latency response when client active
        except Exception:
            time.sleep(0.05)

# HTTP & WebSocket Handlers
async def index_handler(request):
    if HTML_FILE.exists():
        return web.FileResponse(HTML_FILE)
    return web.Response(text="Overlay HTML file not found", status=404)

async def jitter_handler(request):
    if JITTER_FILE.exists():
        return web.FileResponse(JITTER_FILE)
    return web.Response(text="Jitter Overlay HTML file not found", status=404)

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    broadcast_event(data)
                except Exception:
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
    app.router.add_get('/index.html', index_handler)
    app.router.add_get('/jitter', jitter_handler)
    app.router.add_get('/jitter_overlay.html', jitter_handler)
    if (OVERLAY_DIR / "assets").exists():
        app.router.add_static('/assets', OVERLAY_DIR / "assets")
    app.router.add_get('/ws', ws_handler)
    runner = web.AppRunner(app)
    event_loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '127.0.0.1', 8998)
    event_loop.run_until_complete(site.start())
    event_loop.run_forever()

def main():
    # Single-Instance Mutex Guard
    mutex_name = "Global\\OBS_Input_Overlay_Daemon_Mutex"
    mutex = kernel32.CreateMutexW(None, True, mutex_name)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("[InputOverlay] Daemon already running. Exiting cleanly.", flush=True)
        sys.exit(0)

    # 1. Start HTTP / WebSocket Server
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()

    # 2. Start 120 FPS High-Performance Key Poller
    poller_thread = threading.Thread(target=poll_keys_thread, daemon=True)
    poller_thread.start()

    # 3. Install Mouse Hook for Scroll Wheel
    mouse_callback = HOOKPROC(low_level_mouse_proc)
    mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_callback, 0, 0)
    print(f"[InputOverlay] Mouse wheel hook installed: {bool(mouse_hook)}", flush=True)

    # 4. Message Pump for Mouse Hook
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if mouse_hook:
            user32.UnhookWindowsHookEx(mouse_hook)

if __name__ == "__main__":
    main()
