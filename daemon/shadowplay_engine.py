import os
import sys
import time
import json
import shutil
import winsound
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
WATCH_DIRS = [
    Path.home() / "Videos",
    Path(r"F:\Gameplay_Archive\Full_Sessions"),
    Path(r"F:\Gameplay_Archive")
]
CLIPS_BASE_DIR = Path.home() / "Videos" / "Clips"
SIGNATURES_FILE = SCRIPT_DIR / "game_signatures.json"

def load_game_signatures():
    signatures = {
        "r5apex_dx12.exe": "Apex Legends",
        "r5apex.exe": "Apex Legends",
        "MarvelRivals.exe": "Marvel Rivals",
        "Spider-Man2.exe": "Marvel's Spider-Man 2",
        "cs2.exe": "Counter-Strike 2",
        "VALORANT-Win64-Shipping.exe": "Valorant",
        "Overwatch.exe": "Overwatch 2",
        "FortniteClient-Win64-Shipping.exe": "Fortnite",
        "cod.exe": "Call of Duty",
        "Deadlock.exe": "Deadlock"
    }
    if SIGNATURES_FILE.exists():
        try:
            with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
                signatures.update(json.load(f))
        except Exception:
            pass
    return signatures

def detect_active_game():
    """Detects which game process is currently running on the system."""
    signatures = load_game_signatures()
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name')
            if name in signatures:
                return signatures[name]
    except Exception:
        pass
    return "Highlights"

def wait_for_file_ready(filepath, timeout=5.0):
    """Ensures file is fully written and unlocked by OBS before moving."""
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
    """Sorts, renames, and moves the replay clip into game-specific subdirectories."""
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
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "game": game_name,
            "filename": new_filename,
            "path": str(dest_path),
            "size_mb": round(dest_path.stat().st_size / (1024 * 1024), 2)
        }
        with open(meta_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception:
        winsound.Beep(1000, 100)

def main():
    CLIPS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    known_files = set()
    for d in WATCH_DIRS:
        if d.exists():
            known_files.update({str(f.resolve()) for f in d.glob("*.mp4")})

    while True:
        try:
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
