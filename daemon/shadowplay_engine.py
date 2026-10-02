import os
import sys
import time
import json
import shutil
import socket
import struct
import base64
import winsound
import ctypes
from pathlib import Path

# Base directories to watch for incoming OBS clips
WATCH_DIRS = [
    Path.home() / "Videos",
    Path(r"F:\Gameplay_Archive\Full_Sessions"),
    Path(r"F:\Gameplay_Archive")
]
CLIPS_BASE_DIR = Path.home() / "Videos" / "Clips"

# Common game process signatures mapping to human-readable names
GAME_SIGNATURES = {
    "r5apex_dx12.exe": "Apex Legends",
    "r5apex.exe": "Apex Legends",
    "Marvel-Win64-Shipping.exe": "Marvel Rivals",
    "Marvel.exe": "Marvel Rivals",
    "MarvelRivals.exe": "Marvel Rivals",
    "Spider-Man2.exe": "Marvel's Spider-Man 2",
    "cs2.exe": "Counter-Strike 2",
    "VALORANT-Win64-Shipping.exe": "Valorant",
    "Overwatch.exe": "Overwatch 2",
    "FortniteClient-Win64-Shipping.exe": "Fortnite",
    "cod.exe": "Call of Duty",
    "Deadlock.exe": "Deadlock",
    "RocketLeague.exe": "Rocket League",
    "Destiny2.exe": "Destiny 2",
    "Cyberpunk2077.exe": "Cyberpunk 2077",
    "EldenRing.exe": "Elden Ring"
}

# Tailored visual profiles per game
VISUAL_PROFILES = {
    "Apex Legends": {
        "saturation": 1.10,
        "contrast": 0.03,
        "gamma": -0.01,
        "brightness": 0.00,
        "sharpness": 0.04
    },
    "Marvel Rivals": {
        "saturation": 1.03,
        "contrast": 0.01,
        "gamma": 0.00,
        "brightness": 0.00,
        "sharpness": 0.00  # Rivals has in-game DLSS Sharpening (set to 85)
    },
    "Highlights": {
        "saturation": 1.04,
        "contrast": 0.02,
        "gamma": 0.00,
        "brightness": 0.00,
        "sharpness": 0.02
    }
}

def detect_active_game():
    """Detects which game process is currently running."""
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name')
            if name in GAME_SIGNATURES:
                return GAME_SIGNATURES[name]
    except Exception:
        pass
    return "Highlights"

def update_obs_visual_profile(game_name):
    """Dynamically applies the optimal visual profile to OBS Game Capture."""
    profile = VISUAL_PROFILES.get(game_name, VISUAL_PROFILES["Highlights"])
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect(('127.0.0.1', 4455))
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        req = (
            "GET / HTTP/1.1\r\n"
            "Host: 127.0.0.1:4455\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(req.encode('utf-8'))
        resp = s.recv(4096).decode('utf-8', errors='ignore')
        if "101 Switching" not in resp:
            s.close()
            return

        def _send(data):
            raw = json.dumps(data).encode('utf-8')
            hdr = bytearray([0x81])
            mask = os.urandom(4)
            length = len(raw)
            if length < 126:
                hdr.append(0x80 | length)
            elif length < 65536:
                hdr.append(0x80 | 126)
                hdr.extend(struct.pack(">H", length))
            else:
                hdr.append(0x80 | 127)
                hdr.extend(struct.pack(">Q", length))
            hdr.extend(mask)
            masked = bytearray(b ^ mask[i % 4] for i, b in enumerate(raw))
            s.sendall(hdr + masked)

        def _recv():
            hdr = s.recv(2)
            if not hdr: return None
            length = hdr[1] & 127
            if length == 126:
                length = struct.unpack(">H", s.recv(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", s.recv(8))[0]
            payload = b""
            while len(payload) < length:
                chunk = s.recv(length - len(payload))
                if not chunk: break
                payload += chunk
            return json.loads(payload.decode('utf-8'))

        _recv() # Op 0 Hello
        _send({"op": 1, "d": {"rpcVersion": 1}}) # Op 1 Identify
        _recv() # Op 2 Identified

        # Apply Color Correction
        _send({
            "op": 6,
            "d": {
                "requestType": "SetSourceFilterSettings",
                "requestId": "profile_cc",
                "requestData": {
                    "sourceName": "DirectX / Vulkan Game Capture",
                    "filterName": "Color Correction",
                    "filterSettings": {
                        "saturation": profile["saturation"],
                        "contrast": profile["contrast"],
                        "gamma": profile["gamma"],
                        "brightness": profile["brightness"]
                    },
                    "overlay": True
                }
            }
        })
        _recv()

        # Apply Sharpen
        _send({
            "op": 6,
            "d": {
                "requestType": "SetSourceFilterSettings",
                "requestId": "profile_sh",
                "requestData": {
                    "sourceName": "DirectX / Vulkan Game Capture",
                    "filterName": "Sharpen",
                    "filterSettings": {
                        "sharpness": profile["sharpness"]
                    },
                    "overlay": True
                }
            }
        })
        _recv()
        s.close()
    except Exception:
        pass

def wait_for_file_ready(filepath, timeout=15.0):
    """Waits until OBS finishes writing and flushes the file handle."""
    start = time.time()
    last_size = -1
    while time.time() - start < timeout:
        try:
            if not os.path.exists(filepath):
                time.sleep(0.2)
                continue
            cur_size = os.path.getsize(filepath)
            with open(filepath, 'a'):
                pass
            if cur_size > 0 and cur_size == last_size:
                return True
            last_size = cur_size
        except (PermissionError, OSError):
            pass
        time.sleep(0.3)
    return True

def organize_clip(file_path):
    """Renames and moves the saved replay into a game-specific directory."""
    try:
        p = Path(file_path)
        if not p.exists() or p.parent == CLIPS_BASE_DIR:
            return

        game_name = detect_active_game()
        target_dir = CLIPS_BASE_DIR / game_name
        target_dir.mkdir(parents=True, exist_ok=True)

        base_name = p.stem.replace("Replay ", "").replace("Clip_", "").replace(" ", "_")
        clean_game_tag = game_name.replace(" ", "_").replace("'", "")
        new_filename = f"{clean_game_tag}_{base_name}.mp4"
        dest_path = target_dir / new_filename

        wait_for_file_ready(p)
        shutil.move(str(p), str(dest_path))

        # Play ascending confirmation double-beep
        winsound.Beep(1200, 75)
        time.sleep(0.03)
        winsound.Beep(1800, 95)

        # Log metadata
        meta_log = CLIPS_BASE_DIR / "clips_index.jsonl"
        latest_json = CLIPS_BASE_DIR / "latest_clip.json"
        latest_txt = CLIPS_BASE_DIR / "latest_clip_path.txt"
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "game": game_name,
            "filename": new_filename,
            "path": str(dest_path),
            "size_mb": round(dest_path.stat().st_size / (1024 * 1024), 2)
        }
        with open(meta_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)
        with open(latest_txt, "w", encoding="utf-8") as f:
            f.write(str(dest_path))

    except Exception:
        winsound.Beep(1000, 100)

def main():
    # Single-Instance Mutex Guard
    mutex_name = "Global\\OBS_ShadowPlay_Engine_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("[ShadowPlayEngine] Engine already running. Exiting cleanly.", flush=True)
        sys.exit(0)

    CLIPS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    known_files = set()
    for d in WATCH_DIRS:
        if d.exists():
            known_files.update({str(f.resolve()) for f in d.glob("*.mp4")})

    last_game = None
    last_profile_check = 0

    while True:
        try:
            now = time.time()
            # Every 1.5s check active game to dynamically adjust visual profile
            if now - last_profile_check > 1.5:
                current_game = detect_active_game()
                if current_game != last_game:
                    update_obs_visual_profile(current_game)
                    last_game = current_game
                last_profile_check = now

            time.sleep(0.3)
            current_files = set()
            for d in WATCH_DIRS:
                if d.exists():
                    current_files.update({str(f.resolve()) for f in d.glob("*.mp4")})

            new_files = current_files - known_files
            for fpath_str in new_files:
                fpath = Path(fpath_str)
                fname = fpath.name
                if fname.startswith("Replay") or fname.startswith("Clip"):
                    organize_clip(fpath)

            known_files = set()
            for d in WATCH_DIRS:
                if d.exists():
                    known_files.update({str(f.resolve()) for f in d.glob("*.mp4")})
        except Exception:
            time.sleep(1)

if __name__ == "__main__":
    main()
