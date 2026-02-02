# 4K Video Converter (YouTube)

Prosta aplikacja desktopowa w Pythonie do pobierania wideo z YouTube z obsluga jakosci do 4K.

## Wymagania
- Python 3.10+
- `yt-dlp`

## Instalacja
```bash
python -m pip install -r requirements.txt
```

## Uruchomienie
```bash
python main.py
```

## Jak korzystac
1. Wklej link do YouTube.
2. Kliknij "Analizuj" ? aplikacja sprawdzi link i wyswietli dostepne jakosci MP4.
3. Wybierz jakosc i kliknij "Pobierz".

## Domyslna sciezka zapisu
Pliki sa zapisywane do folderu `videos` w katalogu aplikacji.

## FFmpeg (lokalnie, bez PATH)
Umiesc plik `bin/ffmpeg.exe` obok programu, aby mozna bylo scalenie audio+wideo.
Nie trzeba dodawac nic do systemowego PATH.

## Jakosci i MP4
Aplikacja pobiera tylko MP4 (wideo MP4 + audio M4A scalane przez FFmpeg).
Jezeli dana jakosc nie wystepuje w MP4, nie pojawi sie na liscie.

## Build EXE
Windows EXE mozesz zbudowac lokalnie przez `build.bat` (skrypt sam pobierze FFmpeg, jesli go nie ma).
GitHub Actions automatycznie pobierze FFmpeg i zbuduje artefakt EXE.
