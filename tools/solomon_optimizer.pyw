import os
import sys
import time
import json
import socket
import ctypes
import webbrowser
import threading
from pathlib import Path
from ctypes import wintypes

import pystray
from pystray import MenuItem as item, Menu
from PIL import Image, ImageDraw

# Add parent directory to sys.path so we can import solomon_core
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "tools"))
import solomon_core

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

ASSETS_DIR = BASE_DIR / "tools" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
LUMIN_ICON_PATH = ASSETS_DIR / "tray_lumin.png"
VANILLA_ICON_PATH = ASSETS_DIR / "tray_vanilla.png"

# Generate or load high-DPI icons
def create_lumin_icon(size=256):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 10, size-10, size-10], radius=50, fill=(11, 19, 36, 255), outline=(0, 240, 255, 255), width=10)
    d.rounded_rectangle([22, 22, size-22, size-22], radius=40, fill=(15, 23, 42, 255), outline=(0, 150, 255, 120), width=4)
    shield_pts = [
        (size//2, 42),
        (size-48, 88),
        (size-64, 170),
        (size//2, 218),
        (64, 170),
        (48, 88)
    ]
    d.polygon(shield_pts, outline=(0, 243, 255, 255), width=8)
    d.rounded_rectangle([72, 105, size-72, 138], radius=8, fill=(0, 243, 255, 255))
    d.line([(size//2, 148), (size//2, 195)], fill=(0, 243, 255, 220), width=6)
    d.ellipse([size-64, size-64, size-16, size-16], fill=(16, 185, 129, 255), outline=(11, 19, 36, 255), width=8)
    d.ellipse([size-52, size-52, size-28, size-28], fill=(52, 211, 153, 255))
    return img.resize((64, 64), Image.Resampling.LANCZOS)

def create_vanilla_icon(size=256):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 10, size-10, size-10], radius=50, fill=(15, 23, 42, 255), outline=(100, 116, 139, 255), width=8)
    d.rounded_rectangle([22, 22, size-22, size-22], radius=40, fill=(30, 41, 59, 255), outline=(71, 85, 105, 120), width=3)
    shield_pts = [
        (size//2, 46),
        (size-52, 92),
        (size-68, 168),
        (size//2, 214),
        (68, 168),
        (52, 92)
    ]
    d.polygon(shield_pts, outline=(148, 163, 184, 255), width=7)
    d.rounded_rectangle([76, 110, size-76, 136], radius=6, fill=(148, 163, 184, 255))
    d.line([(size//2, 148), (size//2, 192)], fill=(148, 163, 184, 180), width=5)
    d.ellipse([size-64, size-64, size-16, size-16], fill=(71, 85, 105, 255), outline=(15, 23, 42, 255), width=8)
    d.ellipse([size-50, size-50, size-30, size-30], fill=(148, 163, 184, 255))
    return img.resize((64, 64), Image.Resampling.LANCZOS)

if LUMIN_ICON_PATH.exists():
    icon_lumin = Image.open(LUMIN_ICON_PATH)
else:
    icon_lumin = create_lumin_icon()
    icon_lumin.save(LUMIN_ICON_PATH)

if VANILLA_ICON_PATH.exists():
    icon_vanilla = Image.open(VANILLA_ICON_PATH)
else:
    icon_vanilla = create_vanilla_icon()
    icon_vanilla.save(VANILLA_ICON_PATH)

# Global State
config = solomon_core.load_config()
current_status = solomon_core.get_current_status()
tray_icon = None
status_lock = threading.Lock()
is_transitioning = False

def update_tray_state(force_mode=None):
    global current_status
    with status_lock:
        current_status = solomon_core.get_current_status()
        is_lumin = current_status["is_lumin"] if force_mode is None else (force_mode == "lumin")
        
        if tray_icon:
            tray_icon.icon = icon_lumin if is_lumin else icon_vanilla
            status_text = "CPTSOLO Lumin OS" if is_lumin else "True Vanilla PC"
            tray_icon.title = f"Solomon Optimizer [{status_text}]"
            try:
                tray_icon.update_menu()
            except Exception:
                pass

def send_notification(title, message):
    if tray_icon and config.get("notifications", True) and getattr(tray_icon, "HAS_NOTIFICATION", False):
        try:
            tray_icon.notify(title=title, message=message)
        except Exception:
            pass

# Action Handlers
def activate_lumin_os_action(icon=None, item=None):
    global is_transitioning
    if is_transitioning:
        return
    is_transitioning = True
    def task():
        global is_transitioning
        try:
            send_notification("Solomon Optimizer", "Activating CPTSOLO Lumin OS Broadcast Suite...")
            solomon_core.start_lumin_os_mode(launch_obs=True)
            time.sleep(1.5)
            update_tray_state(force_mode="lumin")
            send_notification("CPTSOLO Lumin OS Active", "Overlays on Port 8998, Replay Buffer & OBS Studio are online.")
        finally:
            is_transitioning = False
    threading.Thread(target=task, daemon=True).start()

def activate_vanilla_action(icon=None, item=None):
    global is_transitioning
    if is_transitioning:
        return
    is_transitioning = True
    def task():
        global is_transitioning
        try:
            send_notification("Solomon Optimizer", "Switching to True Vanilla PC Mode...")
            solomon_core.stop_all_stream_services(kill_obs=True)
            time.sleep(1.0)
            update_tray_state(force_mode="vanilla")
            send_notification("True Vanilla PC Mode Active", "Port 8998 released. Stream daemons stopped. Zero input latency.")
        finally:
            is_transitioning = False
    threading.Thread(target=task, daemon=True).start()

def toggle_auto_sync_action(icon=None, item=None):
    config["auto_sync_obs"] = not config.get("auto_sync_obs", True)
    solomon_core.save_config(config)
    state_str = "Enabled" if config["auto_sync_obs"] else "Disabled"
    send_notification("Solomon Optimizer", f"OBS Auto-Sync has been {state_str}.")
    update_tray_state()

def set_boot_vanilla_action(icon=None, item=None):
    solomon_core.set_boot_profile("vanilla")
    config["boot_profile"] = "vanilla"
    solomon_core.save_config(config)
    send_notification("Boot Profile Changed", "Set to Vanilla Clean. Scheduled tasks disabled at startup.")
    update_tray_state()

def set_boot_lumin_action(icon=None, item=None):
    solomon_core.set_boot_profile("lumin")
    config["boot_profile"] = "lumin"
    solomon_core.save_config(config)
    send_notification("Boot Profile Changed", "Set to Lumin OS. Stream suite will auto-start at logon.")
    update_tray_state()

def emergency_kill_action(icon=None, item=None):
    def task():
        send_notification("Solomon Optimizer", "Force killing all stream background daemons...")
        solomon_core.stop_all_stream_services(kill_obs=False)
        time.sleep(1.0)
        update_tray_state()
        send_notification("Port 8998 Released", "All stream overlay daemons and hooks terminated.")
    threading.Thread(target=task, daemon=True).start()

def open_url_action(url):
    return lambda icon, item: webbrowser.open(url)

def exit_action(icon, item):
    icon.stop()

# Build S+ Tier Menu
def build_menu():
    return Menu(
        item(
            lambda item: f"👑 Solomon Optimizer  [{'CPTSOLO Lumin OS' if current_status['is_lumin'] else 'True Vanilla PC'}]",
            lambda icon, item: None,
            enabled=False
        ),
        item(
            lambda item: f"  {'●' if current_status['obs_running'] else '○'} OBS Studio: {'Running' if current_status['obs_running'] else 'Closed'}",
            lambda icon, item: None,
            enabled=False
        ),
        item(
            lambda item: f"  {'●' if current_status['port_8998_active'] else '○'} Port 8998 Overlay: {'Active' if current_status['port_8998_active'] else 'Released'}",
            lambda icon, item: None,
            enabled=False
        ),
        item(
            lambda item: f"  {'●' if 'Vanilla' in current_status['boot_profile'] else '○'} Boot Profile: {current_status['boot_profile']}",
            lambda icon, item: None,
            enabled=False
        ),
        Menu.SEPARATOR,
        item(
            "⚡ Activate CPTSOLO Lumin OS (Stream Suite)",
            activate_lumin_os_action
        ),
        item(
            "🍃 Activate True Vanilla PC (Zero Latency)",
            activate_vanilla_action
        ),
        Menu.SEPARATOR,
        item(
            lambda item: f"🔄 Auto-Sync with OBS: {'[✔ Enabled]' if config.get('auto_sync_obs', True) else '[✖ Disabled]'}",
            toggle_auto_sync_action
        ),
        item(
            "🚀 Boot Profile",
            Menu(
                item(
                    "Vanilla Clean (Zero Boot Overhead)",
                    set_boot_vanilla_action,
                    checked=lambda item: "vanilla" in current_status.get("boot_profile", "").lower()
                ),
                item(
                    "Lumin OS (Auto-Start on Logon)",
                    set_boot_lumin_action,
                    checked=lambda item: "lumin" in current_status.get("boot_profile", "").lower()
                )
            )
        ),
        item(
            "🌐 Stream Overlays",
            Menu(
                item("🎯 Ultra Hybrid Apex HUD", open_url_action("http://127.0.0.1:8998/ultra")),
                item("🎵 Live Spotify HUD", open_url_action("http://127.0.0.1:8998/spotify")),
                item("🏆 TAS.gg Apex Rank Tracker", open_url_action("https://overlays.tas.gg/217857230/98130/rp-games-nextrank-cycle")),
                item("📷 Cyber Webcam Frame", open_url_action("http://127.0.0.1:8998/assets/camera_mask.png")),
                Menu.SEPARATOR,
                item("📊 Overlay Root (Port 8998)", open_url_action("http://127.0.0.1:8998"))
            )
        ),
        Menu.SEPARATOR,
        item("🛑 Force Free Port 8998 & Kill Daemons", emergency_kill_action),
        item("🔄 Refresh Telemetry Status", lambda icon, item: update_tray_state()),
        Menu.SEPARATOR,
        item("🚪 Exit Solomon Optimizer", exit_action)
    )

# Background Watchdog with Auto-Sync
def obs_watchdog_thread():
    last_obs_state = solomon_core.is_obs_running()
    consecutive_absent = 0
    
    while True:
        try:
            time.sleep(1.5)
            if is_transitioning:
                continue
                
            obs_now = solomon_core.is_obs_running()
            auto_sync = config.get("auto_sync_obs", True)
            
            # OBS was launched externally
            if obs_now and not last_obs_state:
                last_obs_state = True
                consecutive_absent = 0
                if auto_sync and not solomon_core.is_daemon_running():
                    send_notification("Solomon Optimizer", "OBS Studio detected. Auto-launching Stream Overlays...")
                    solomon_core.start_lumin_os_mode(launch_obs=False)
                    time.sleep(1.0)
                update_tray_state(force_mode="lumin")
                
            # OBS was closed externally
            elif not obs_now and last_obs_state:
                consecutive_absent += 1
                if consecutive_absent >= 2:  # 3 seconds confirmation
                    last_obs_state = False
                    consecutive_absent = 0
                    if auto_sync and solomon_core.is_daemon_running():
                        send_notification("Solomon Optimizer", "OBS Studio closed. Auto-releasing Port 8998 & Daemons...")
                        solomon_core.stop_all_stream_services(kill_obs=False)
                        time.sleep(1.0)
                    update_tray_state(force_mode="vanilla")
            else:
                if not obs_now:
                    consecutive_absent = 0
                # Periodic telemetry sync
                update_tray_state()
                
        except Exception:
            pass

def main():
    # Single-Instance Mutex Guard for the Tray App
    mutex_name = "Global\\Solomon_Optimizer_Tray_Mutex"
    mutex = kernel32.CreateMutexW(None, True, mutex_name)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("[Solomon Optimizer] Tray application is already running.", flush=True)
        sys.exit(0)

    global tray_icon
    initial_icon = icon_lumin if current_status["is_lumin"] else icon_vanilla
    initial_title = f"Solomon Optimizer [{'CPTSOLO Lumin OS' if current_status['is_lumin'] else 'True Vanilla PC'}]"

    tray_icon = pystray.Icon(
        name="Solomon Optimizer",
        icon=initial_icon,
        title=initial_title,
        menu=build_menu()
    )

    # Start Watchdog Thread
    watchdog = threading.Thread(target=obs_watchdog_thread, daemon=True)
    watchdog.start()

    # Run System Tray
    tray_icon.run()

if __name__ == "__main__":
    main()
