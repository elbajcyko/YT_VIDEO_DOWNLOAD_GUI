import os
from dataclasses import dataclass
import yt_dlp

BASE_DIR = os.path.dirname(__file__)
FFMPEG_PATH = os.path.join(BASE_DIR, "bin", "ffmpeg.exe")


@dataclass
class DownloadOptions:
    url: str
    output_dir: str
    quality: str
    fmt: str


class Downloader:
    def __init__(self, progress_cb=None, log_cb=None, status_cb=None):
        self.progress_cb = progress_cb
        self.log_cb = log_cb
        self.status_cb = status_cb
        self._last_status = ""
        self._cancel_requested = False
        self._last_filename = ""
        self._last_tmpfilename = ""

    def analyze(self, url: str):
        ydl_opts = {
            "noplaylist": True,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise RuntimeError(self._normalize_error(str(exc))) from exc

        formats = info.get("formats") or []
        # MP4 video streams (can be merged with M4A audio via FFmpeg).
        heights = sorted(
            {
                f.get("height")
                for f in formats
                if f.get("vcodec") not in (None, "none") and f.get("ext") == "mp4"
            },
            reverse=True,
        )
        available = [f"{h}p" for h in heights if isinstance(h, int)]
        return {
            "title": info.get("title") or "",
            "available_qualities": available,
        }

    def download(self, options: DownloadOptions):
        self._cancel_requested = False
        self._last_filename = ""
        self._last_tmpfilename = ""
        os.makedirs(options.output_dir, exist_ok=True)
        output_template = os.path.join(options.output_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "noplaylist": True,
            "progress_hooks": [self._progress_hook],
            "merge_output_format": "mp4",
            "format": self._build_format(options),
        }
        if self._needs_ffmpeg(ydl_opts["format"]):
            if not os.path.exists(FFMPEG_PATH):
                raise RuntimeError(
                    "Brak lokalnego FFmpeg. Umiesc plik bin/ffmpeg.exe obok aplikacji."
                )
            ydl_opts["ffmpeg_location"] = FFMPEG_PATH

        self._log(f"Start pobierania: {options.url}")
        self._log(f"Format: {options.fmt.upper()}, jakosc: {options.quality}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([options.url])
        except yt_dlp.utils.DownloadError as exc:
            raise RuntimeError(self._normalize_error(str(exc))) from exc

    def _build_format(self, options: DownloadOptions):
        quality = options.quality
        if quality == "auto":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"

        height = int(quality.replace("p", ""))

        # MP4 video + M4A audio (requires FFmpeg to merge).
        return (
            f"bestvideo[ext=mp4][height={height}]+bestaudio[ext=m4a]/"
            f"bestvideo[ext=mp4][height<={height}]+bestaudio[ext=m4a]/"
            f"best[ext=mp4][height<={height}]"
        )

    def _progress_hook(self, data):
        filename = data.get("filename")
        tmpfilename = data.get("tmpfilename")
        if filename:
            self._last_filename = filename
        if tmpfilename:
            self._last_tmpfilename = tmpfilename
        if self._cancel_requested:
            raise yt_dlp.utils.DownloadError("Cancelled by user")
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            if total:
                percent = data.get("downloaded_bytes", 0) * 100 / total
                if self.progress_cb:
                    self.progress_cb(round(percent, 2))
            status = self._format_progress_status(data)
            if status and status != self._last_status:
                self._last_status = status
                if self.status_cb:
                    self.status_cb(status)
        elif data.get("status") == "finished":
            if self.progress_cb:
                self.progress_cb(100.0)
            self._log("Pobieranie zakonczone, trwa przetwarzanie...")
            if self.status_cb:
                self.status_cb("Pobieranie zakonczone, trwa przetwarzanie...")

    def _log(self, message):
        if self.log_cb:
            self.log_cb(message)

    def _normalize_error(self, message):
        if "Unsupported URL" in message:
            return "Nieobslugiwany lub bledny link."
        if "HTTP Error 403" in message:
            return "Brak dostepu lub ograniczenia sieciowe (HTTP 403)."
        if "Requested format is not available" in message:
            return "Wybrana jakosc nie jest dostepna dla tego wideo."
        if "ffmpeg" in message.lower():
            return "Brak FFmpeg. Umiesc bin/ffmpeg.exe obok aplikacji (bez PATH)."
        return message

    def _needs_ffmpeg(self, fmt: str) -> bool:
        return "bestvideo" in fmt

    def cancel(self):
        self._cancel_requested = True

    def cleanup_temp(self):
        candidates = []
        if self._last_filename:
            candidates.append(self._last_filename)
            candidates.append(self._last_filename + ".part")
        if self._last_tmpfilename:
            candidates.append(self._last_tmpfilename)
            candidates.append(self._last_tmpfilename + ".part")
        for path in candidates:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def _format_progress_status(self, data) -> str:
        percent_value = data.get("downloaded_bytes")
        total_value = data.get("total_bytes") or data.get("total_bytes_estimate")
        speed_value = data.get("speed")
        eta_value = data.get("eta")
        if percent_value is None and total_value is None and speed_value is None and eta_value is None:
            return ""
        parts = []
        percent = ""
        if percent_value is not None and total_value:
            percent = round((percent_value / total_value) * 100)
        if percent != "":
            parts.append(f"Pobrano {percent}%")
        if speed_value:
            mb_s = speed_value / 1_000_000
            parts.append(f"{mb_s:.1f}mb/s")
        if eta_value is not None:
            if eta_value >= 60:
                parts.append(f"Pozostalo: {eta_value // 60}min")
            else:
                parts.append(f"Pozostalo: {eta_value}s")
        return ", ".join(parts)
