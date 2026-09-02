# OmaAmp ⚡🎵

A genuine, standalone **Winamp 2.91 Classic Audio Player** built with Python and Qt for Linux & Omarchy.

Featuring modular magnetic docking windows, real-time animated spectrum analyzer / oscilloscope, retro 7-segment green phosphor LED time display, marquee scrolling track screen, 10-band graphic equalizer with presets, drag-and-drop playlist editor, and a fully customizable theme engine!

![OmaAmp Preview](./screenshot.png)

---

## 🎛️ Key Features

* **📻 Authentic Winamp 2.91 Main Player:**
  * **7-Segment LED Clock:** Displays elapsed or remaining track time (`-03:45`) with ghost LCD back-lighting. Click the time digits to toggle mode!
  * **Real-time Spectrum Visualizer:** 19-band frequency visualizer with falling peak dots. Click the visualizer box to switch between **Spectrum Analyzer** and **Oscilloscope Waveform**!
  * **Marquee LCD Screen:** Smooth scrolling song title and artist.
  * **Specs Readout:** Real-time bitrate (`320 kbps`), sample rate (`44.1 kHz`), and `STEREO` / `MONO` indicator lights.
  * **Controls:** `|<<` (Prev), `▶` (Play), `❚❚` (Pause), `■` (Stop), `>>|` (Next), `⏏` (Eject/Open).
  * **Sliders:** Master Volume (`VOL`), Left/Right Balance (`BAL`), and Track Seek Position (`POSITION`).
  * **Modes:** `SHUF` (Shuffle) and `REP` (Repeat).

* **🎚️ 10-Band Graphic Equalizer (`EQ`):**
  * 10 frequency bands (60Hz, 170Hz, 310Hz, 600Hz, 1kHz, 3kHz, 6kHz, 12kHz, 14kHz, 16kHz) + Preamp slider.
  * Live frequency response curve graph.
  * One-click presets: *Rock, Pop, Techno, Dance, Full Bass, Full Treble, Club, Classical, Live, Flat*.
  * `ZERO` button to reset all bands instantly.

* **📜 Drag & Drop Playlist Editor (`PL`):**
  * **Drag & Drop:** Simply drag MP3, FLAC, WAV, OGG, or AAC files and whole folders straight from your file manager into OmaAmp!
  * Instant search filter to find tracks in massive libraries.
  * Active playing song highlighted with gold glow.
  * Total playlist statistics (e.g. `14 tracks / 52:10 min`).
  * `+ FILE`, `+ DIR`, `- REM`, and `CLEAR` buttons.

* **🎨 Custom Themes & Skin Engine:**
  * Comes with 4 built-in themes:
    1. **Classic Retro Winamp:** Iconic gunmetal chassis with green LED phosphor.
    2. **Modern Obsidian & Cyan:** Sleek obsidian surfaces with high-contrast cyan glow.
    3. **Cyberpunk Neon 2077:** Hot pink, neon cyan, and deep purple.
    4. **Amber Phosphor CRT:** Vintage monochrome amber terminal feel.
  * **Built-in Theme Editor:** Click the **`SKIN`** button in the titlebar to switch themes in real-time or click **`🎨 Create / Edit Custom Theme`** to customize any color and save directly into `~/.config/omaamp/themes/`!

---

## 🚀 How to Launch

### Launch via Terminal:
```bash
omaamp
```
Or open audio files directly:
```bash
omaamp ~/Music/*.mp3
```

### Launch via Application Menu:
Press `Super + Space` (or your app launcher) and search for **OmaAmp**!

---

## 🎨 How to Create Custom Themes

OmaAmp stores user themes in `~/.config/omaamp/themes/`.

To create a new theme manually, create a JSON file (e.g. `~/.config/omaamp/themes/my_theme.json`):

```json
{
  "id": "my_theme",
  "name": "My Custom Theme",
  "author": "Your Name",
  "description": "Custom color palette for OmaAmp",
  "colors": {
    "chassis_bg": "#1e1e24",
    "chassis_border": "#3c3c4a",
    "panel_bg": "#000000",
    "titlebar_bg": "#141418",
    "titlebar_text": "#00e5ff",
    "lcd_bg": "#020902",
    "lcd_text": "#00ff66",
    "lcd_text_dim": "#003b0c",
    "lcd_kbps": "#00dd22",
    "vis_bg": "#000000",
    "vis_bars_low": "#00ff44",
    "vis_bars_mid": "#ffea00",
    "vis_bars_high": "#ff2200",
    "vis_peaks": "#ffffff",
    "vis_oscilloscope": "#00ff66",
    "button_bg": "#2a2a34",
    "button_border": "#444456",
    "button_text": "#d4d8e8",
    "button_active": "#00ff66",
    "slider_trough": "#0a0a0e",
    "slider_thumb": "#5a5d72",
    "playlist_bg": "#0a0a0f",
    "playlist_text": "#00ff44",
    "playlist_selected_bg": "#003318",
    "playlist_selected_text": "#ffffff",
    "playlist_playing_text": "#ffcc00",
    "playlist_playing_bg": "#222000"
  }
}
```
Open OmaAmp, click **`SKIN`**, and your theme will appear immediately in the list!

---

## 📂 Project Structure

```
OmaAmp/
├── main.py                  # Entry point & application controller
├── omaamp                   # Executable bash launcher
├── omaamp.desktop           # Linux Desktop entry
├── icon.png                 # Retro app icon
├── core/
│   ├── audio_engine.py      # Playback engine, playlist queue, metadata parser
│   ├── config.py            # User configuration (~/.config/omaamp/config.json)
│   ├── theme_manager.py     # Theme loader & hot-swapper (~/.config/omaamp/themes/)
│   └── visualizer_data.py   # Spectrum analyzer & oscilloscope mathematics
├── ui/
│   ├── main_window.py       # Main Winamp player window
│   ├── visualizer_widget.py # Spectrum analyzer & oscilloscope canvas
│   ├── lcd_display.py       # 7-Segment LED time + marquee display
│   ├── equalizer_window.py  # 10-Band graphic EQ window
│   ├── playlist_window.py   # Drag & drop Playlist editor
│   └── theme_dialog.py      # Theme picker & custom theme creator
├── themes/
│   ├── classic_retro.json   # Authentic Winamp 2.91 theme
│   ├── modern_dark.json     # Modern obsidian theme
│   ├── cyberpunk_neon.json  # Cyberpunk neon theme
│   └── amber_phosphor.json  # Amber CRT terminal theme
└── README.md
```

---

## 📄 License

MIT License © 2026 [Alex Weström](https://github.com/alexwest1981)
