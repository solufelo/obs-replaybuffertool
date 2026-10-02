import os
import sys
import json
import time
import socket
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "tools" / "solomon_config.json"
PYTHONW = r"C:\Python314\pythonw.exe"
if not Path(PYTHONW).exists():
    PYTHONW = sys.executable

DEFAULT_CONFIG = {
    "auto_sync_obs": True,
    "boot_profile": "vanilla",
    "notifications": True
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

import ctypes
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x00000002

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.c_size_t),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', wintypes.WCHAR * 260)
    ]

def is_port_in_use(port=8998):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(('127.0.0.1', port)) == 0

def is_obs_running():
    kernel32 = ctypes.windll.kernel32
    hSnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if hSnap == -1:
        return False
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    found = False
    if kernel32.Process32FirstW(hSnap, ctypes.byref(pe)):
        while True:
            if pe.szExeFile.lower() == "obs64.exe":
                found = True
                break
            if not kernel32.Process32NextW(hSnap, ctypes.byref(pe)):
                break
    kernel32.CloseHandle(hSnap)
    return found

def is_daemon_running():
    return is_port_in_use(8998)

def get_current_status():
    obs = is_obs_running()
    daemon = is_daemon_running()
    port = is_port_in_use(8998)
    boot = get_boot_profile()
    is_lumin = obs or daemon or port
    return {
        "mode": "Lumin OS Mode" if is_lumin else "Vanilla PC Mode",
        "is_lumin": is_lumin,
        "obs_running": obs,
        "daemon_running": daemon,
        "port_8998_active": port,
        "boot_profile": boot
    }

def get_boot_profile():
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-ScheduledTask -TaskName 'OBS_Input_Overlay' -ErrorAction SilentlyContinue).State"],
            creationflags=0x08000000,
            text=True
        ).strip()
        if "Disabled" in out:
            return "Vanilla (Clean)"
        return "Lumin OS (Auto-Start)"
    except Exception:
        return "Vanilla (Clean)"

def set_boot_profile(mode="vanilla"):
    cfg = load_config()
    cfg["boot_profile"] = mode
    save_config(cfg)
    try:
        if mode == "vanilla":
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-ScheduledTask -TaskName 'OBS_*' -ErrorAction SilentlyContinue | Disable-ScheduledTask"],
                creationflags=0x08000000,
                check=False
            )
        else:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-ScheduledTask -TaskName 'OBS_*' -ErrorAction SilentlyContinue | Enable-ScheduledTask"],
                creationflags=0x08000000,
                check=False
            )
    except Exception:
        pass

def clear_obs_sentinels():
    try:
        sentinel_dir = Path.home() / "AppData" / "Roaming" / "obs-studio" / ".sentinel"
        if sentinel_dir.exists():
            for f in os.listdir(sentinel_dir):
                try:
                    (sentinel_dir / f).unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

def start_lumin_os_mode(launch_obs=True):
    clear_obs_sentinels()

    # 1. Start Input Daemon if not running
    if not is_daemon_running():
        daemon_script = str(BASE_DIR / "daemon" / "input_overlay_daemon.py")
        subprocess.Popen(
            [PYTHONW, daemon_script, "--auto-exit-with-obs"],
            cwd=str(BASE_DIR),
            creationflags=0x08000000
        )
        time.sleep(1.0)

    # 2. Start ShadowPlay Engine if not running
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | Where-Object { $_.CommandLine -match 'shadowplay_engine' } | Select-Object -ExpandProperty ProcessId"],
            creationflags=0x08000000,
            text=True
        ).strip()
        if not out:
            engine_script = str(BASE_DIR / "daemon" / "shadowplay_engine.py")
            subprocess.Popen(
                [PYTHONW, engine_script],
                cwd=str(BASE_DIR),
                creationflags=0x08000000
            )
    except Exception:
        pass

    # 3. Launch OBS Studio directly if requested and not running
    if launch_obs and not is_obs_running():
        obs_exe = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
        obs_dir = r"C:\Program Files\obs-studio\bin\64bit"
        if Path(obs_exe).exists():
            subprocess.Popen(
                [obs_exe, "--startreplaybuffer", "--minimize-to-tray", "--scene", "GAMEPLAY ULTRA (Active)"],
                cwd=obs_dir,
                creationflags=0x08000000
            )
            time.sleep(1.5)

    return get_current_status()

def stop_all_stream_services(kill_obs=True):
    # 1. Stop OBS if requested
    if kill_obs:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Process obs64 -ErrorAction SilentlyContinue | Stop-Process -Force"],
                creationflags=0x08000000,
                check=False
            )
        except Exception:
            pass

    # Clear stale crash sentinels so OBS never prompts for Safe Mode
    sentinel_dir = Path.home() / "AppData" / "Roaming" / "obs-studio" / ".sentinel"
    if sentinel_dir.exists():
        for f in sentinel_dir.glob("*"):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

    # 2. Stop Python Daemons (input overlay, shadowplay engine, beep watcher)
    ps_cmd = """
    Get-CimInstance Win32_Process | Where-Object { 
        $_.CommandLine -match 'input_overlay_daemon|shadowplay_engine|clip_beep_watcher|media_watcher_service' 
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            creationflags=0x08000000,
            check=False
        )
    except Exception:
        pass

    # 3. Stop Scheduled Tasks if currently in Running state
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-ScheduledTask -TaskName 'OBS_*' -ErrorAction SilentlyContinue | Stop-ScheduledTask -ErrorAction SilentlyContinue"],
            creationflags=0x08000000,
            check=False
        )
    except Exception:
        pass

    # 4. Wait for port 8998 to be free
    for _ in range(10):
        if not is_port_in_use(8998):
            break
        time.sleep(0.3)

    return get_current_status()

if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "status"
    if action == "lumin":
        print("Activating CPTSOLO Lumin OS Mode...")
        res = start_lumin_os_mode(launch_obs=True)
        print(json.dumps(res, indent=2))
    elif action == "vanilla":
        print("Activating True Vanilla PC Mode...")
        res = stop_all_stream_services(kill_obs=True)
        print(json.dumps(res, indent=2))
    elif action == "boot-vanilla":
        set_boot_profile("vanilla")
        print("Boot profile set to: Vanilla (Clean - No Startup Overhead)")
    elif action == "boot-lumin":
        set_boot_profile("lumin")
        print("Boot profile set to: Lumin OS (Auto-Start at Logon)")
    else:
        print(json.dumps(get_current_status(), indent=2))
