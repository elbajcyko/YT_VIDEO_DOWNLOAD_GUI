import json
import os
import sys
from dataclasses import dataclass


def _app_dir() -> str:
    # When frozen (PyInstaller), __file__ points into _internal; use the exe folder instead.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


BASE_DIR = _app_dir()
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "videos")


@dataclass
class Settings:
    output_dir: str


class SettingsStore:
    def load(self) -> Settings:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                output_dir = data.get("output_dir") or DEFAULT_OUTPUT
                # Migrate old default (base dir) to ./videos
                if os.path.abspath(output_dir) == os.path.abspath(BASE_DIR):
                    output_dir = DEFAULT_OUTPUT
                return Settings(output_dir=output_dir)
            except Exception:
                pass
        return Settings(output_dir=DEFAULT_OUTPUT)

    def save(self, settings: Settings):
        data = {
            "output_dir": settings.output_dir,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
