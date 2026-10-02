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
    0x50: "STIM",     # 'P' (Tactical / Stim)
    0x12: "STIM",     # Alt (Tactical / Stim)
    0xA4: "STIM",     # Left Alt (Swapped for P!)
    0x51: "STIM",     # 'Q' (Tactical fallback)
    0x45: "INTERACT", # 'E'
    0x43: "CROUCH",   # 'C'
    0x11: "CROUCH",   # Ctrl
    0xA2: "CROUCH",   # Left Ctrl
    0x20: "JUMP",     # Space
    0x10: "SPRINT",   # Shift
    0x31: "WEAPON1",  # 1
    0x32: "WEAPON2",  # 2
    0x33: "HOLSTER",  # 3 (Holster)
    0x34: "HEAL",     # 4 (Heal)
    0x05: "HOLSTER",  # Mouse 4 (Holster in user config)
    0x06: "HEAL",     # Mouse 5 (Heal in user config)
    0x01: "LMB",
    0x02: "RMB"
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
            try:
                asyncio.run_coroutine_threadsafe(ws.send_str(msg), event_loop)
            except Exception:
                pass

# Low-level Mouse Hook for Scroll Wheel (Tap-Strafe & Bunny Hop detection)
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
