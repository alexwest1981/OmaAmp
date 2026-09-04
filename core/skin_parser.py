import os
import zipfile
from PyQt6.QtGui import QImage, QPixmap, QColor

class WinampSkin:
    def __init__(self, name="Classic", filepath=None):
        self.name = name
        self.filepath = filepath
        self.is_wsz = True
        self.colors = {}
        self.vis_colors = []  # 24 QColors from VISCOLOR.TXT
        self.bitmaps = {}
        self.sprites = {}
        
        if filepath:
            self.load(filepath)

    def load(self, filepath):
        self.filepath = filepath
        self.name = os.path.splitext(os.path.basename(filepath))[0].replace("_", " ")

        if os.path.isfile(filepath) and filepath.lower().endswith(('.wsz', '.zip')):
            self._load_from_zip(filepath)
        elif os.path.isdir(filepath):
            self._load_from_dir(filepath)

        self._slice_sprites()
        self._extract_theme_colors()

    def _load_from_zip(self, zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                name_map = {n.lower(): n for n in z.namelist()}

                for lower_name, real_name in name_map.items():
                    if lower_name.endswith(('.bmp', '.png')):
                        base_key = os.path.splitext(os.path.basename(lower_name))[0]
                        data = z.read(real_name)
                        img = QImage.fromData(data)
                        if not img.isNull():
                            self.bitmaps[base_key] = img
                    elif lower_name.endswith('viscolor.txt'):
                        text_data = z.read(real_name).decode('latin-1', errors='ignore')
                        self._parse_viscolor(text_data)
                    elif lower_name.endswith('pledit.txt'):
                        text_data = z.read(real_name).decode('latin-1', errors='ignore')
                        self._parse_pledit_txt(text_data)
        except Exception as e:
            print(f"Error loading WSZ skin {zip_path}: {e}")

    def _load_from_dir(self, dir_path):
        for root, _, files in os.walk(dir_path):
            for f in files:
                lower = f.lower()
                fpath = os.path.join(root, f)
                if lower.endswith(('.bmp', '.png')):
                    base_key = os.path.splitext(lower)[0]
                    img = QImage(fpath)
                    if not img.isNull():
                        self.bitmaps[base_key] = img
                elif lower == 'viscolor.txt':
                    with open(fpath, 'r', encoding='latin-1', errors='ignore') as vf:
                        self._parse_viscolor(vf.read())
                elif lower == 'pledit.txt':
                    with open(fpath, 'r', encoding='latin-1', errors='ignore') as pf:
                        self._parse_pledit_txt(pf.read())

    def _parse_viscolor(self, text):
        lines = text.strip().splitlines()
        self.vis_colors = []
        for line in lines:
            line = line.split('//')[0].strip().rstrip(';,')
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    r = int(parts[0].strip())
                    g = int(parts[1].strip())
                    b = int(parts[2].strip())
                    self.vis_colors.append(QColor(r, g, b))
                except Exception:
                    pass

    def _parse_pledit_txt(self, text):
        lines = text.strip().splitlines()
        for line in lines:
            line = line.split(';')[0].strip()
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip().lower()
                v = v.strip().lstrip('#')
                if len(v) == 6:
                    hex_col = f"#{v}"
                    if k == 'normal':
                        self.colors['playlist_text'] = hex_col
                    elif k == 'current':
                        self.colors['playlist_playing_text'] = hex_col
                    elif k == 'normalbg':
                        self.colors['playlist_bg'] = hex_col
                    elif k == 'selectedbg':
                        self.colors['playlist_selected_bg'] = hex_col

    def _slice_sprites(self):
        # 1. Transport Buttons (Cbuttons.bmp)
        cbuttons = self.bitmaps.get('cbuttons')
        if cbuttons:
            self.sprites['btn_prev'] = (
                QPixmap.fromImage(cbuttons.copy(0, 0, 23, 18)),
                QPixmap.fromImage(cbuttons.copy(0, 18, 23, 18))
            )
            self.sprites['btn_play'] = (
                QPixmap.fromImage(cbuttons.copy(23, 0, 23, 18)),
                QPixmap.fromImage(cbuttons.copy(23, 18, 23, 18))
            )
            self.sprites['btn_pause'] = (
                QPixmap.fromImage(cbuttons.copy(46, 0, 23, 18)),
                QPixmap.fromImage(cbuttons.copy(46, 18, 23, 18))
            )
            self.sprites['btn_stop'] = (
                QPixmap.fromImage(cbuttons.copy(69, 0, 23, 18)),
                QPixmap.fromImage(cbuttons.copy(69, 18, 23, 18))
            )
            self.sprites['btn_next'] = (
                QPixmap.fromImage(cbuttons.copy(92, 0, 22, 18)),
                QPixmap.fromImage(cbuttons.copy(92, 18, 22, 18))
            )
            if cbuttons.width() >= 136:
                self.sprites['btn_eject'] = (
                    QPixmap.fromImage(cbuttons.copy(114, 0, 22, 16)),
                    QPixmap.fromImage(cbuttons.copy(114, 16, 22, 16))
                )

        # 2. LED Numbers (Numbers.bmp)
        numbers = self.bitmaps.get('numbers')
        if numbers:
            digit_w = 9
            digit_h = 13
            self.sprites['digits'] = [
                QPixmap.fromImage(numbers.copy(i * digit_w, 0, digit_w, digit_h))
                for i in range(10)
            ]
            if numbers.width() >= 99:
                self.sprites['digit_blank'] = QPixmap.fromImage(numbers.copy(90, 0, digit_w, digit_h))
            if numbers.width() >= 108:
                self.sprites['digit_minus'] = QPixmap.fromImage(numbers.copy(99, 0, digit_w, digit_h))

        # 3. Shuffle / Repeat / EQ / PL (Shufrep.bmp)
        shufrep = self.bitmaps.get('shufrep')
        if shufrep:
            # Repeat
            self.sprites['btn_rep'] = (
                QPixmap.fromImage(shufrep.copy(0, 0, 28, 15)),
                QPixmap.fromImage(shufrep.copy(0, 15, 28, 15))
            )
            # Shuffle
            self.sprites['btn_shuf'] = (
                QPixmap.fromImage(shufrep.copy(28, 0, 47, 15)),
                QPixmap.fromImage(shufrep.copy(28, 15, 47, 15))
            )
            # EQ & PL
            if shufrep.height() >= 73:
                self.sprites['btn_eq'] = (
                    QPixmap.fromImage(shufrep.copy(0, 61, 23, 12)),
                    QPixmap.fromImage(shufrep.copy(46, 61, 23, 12))
                )
                self.sprites['btn_pl'] = (
                    QPixmap.fromImage(shufrep.copy(23, 61, 23, 12)),
                    QPixmap.fromImage(shufrep.copy(69, 61, 23, 12))
                )

        # 4. Playlist Buttons (Pledit.bmp)
        pledit = self.bitmaps.get('pledit')
        if pledit and pledit.width() >= 260 and pledit.height() >= 100:
            self.sprites['pl_btn_add'] = (
                QPixmap.fromImage(pledit.copy(11, 81, 22, 18)),
                QPixmap.fromImage(pledit.copy(11, 81, 22, 18))
            )
            self.sprites['pl_btn_rem'] = (
                QPixmap.fromImage(pledit.copy(40, 81, 22, 18)),
                QPixmap.fromImage(pledit.copy(40, 81, 22, 18))
            )
            self.sprites['pl_btn_sel'] = (
                QPixmap.fromImage(pledit.copy(70, 81, 22, 18)),
                QPixmap.fromImage(pledit.copy(70, 81, 22, 18))
            )
            self.sprites['pl_btn_misc'] = (
                QPixmap.fromImage(pledit.copy(100, 81, 22, 18)),
                QPixmap.fromImage(pledit.copy(100, 81, 22, 18))
            )
            self.sprites['pl_btn_list'] = (
                QPixmap.fromImage(pledit.copy(232, 81, 22, 18)),
                QPixmap.fromImage(pledit.copy(232, 81, 22, 18))
            )

        # 5. Masked Slider Knob PNG
        eqmain = self.bitmaps.get('eqmain')
        eq_ex = self.bitmaps.get('eq_ex')
        knob_img = None
        if eqmain and not eqmain.isNull() and eqmain.width() >= 92 and eqmain.height() >= 70:
            knob_img = eqmain.copy(78, 59, 14, 11).convertToFormat(QImage.Format.Format_ARGB32)
            for pt in [(0,0), (1,0), (0,1), (12,0), (13,0), (13,1), (0,9), (0,10), (1,10), (13,9), (12,10), (13,10)]:
                knob_img.setPixelColor(pt[0], pt[1], QColor(0, 0, 0, 0))
        elif eq_ex and not eq_ex.isNull() and eq_ex.width() >= 14:
            knob_img = eq_ex.copy(0, 0, 14, 11).convertToFormat(QImage.Format.Format_ARGB32)

        if knob_img:
            cache_dir = os.path.expanduser("~/.config/omaamp/cache")
            os.makedirs(cache_dir, exist_ok=True)
            knob_scaled = knob_img.scaled(20, 15)
            self.knob_path = os.path.join(cache_dir, f"knob_{os.path.basename(self.filepath or 'skin')}.png")
            knob_scaled.save(self.knob_path)
        else:
            self.knob_path = None

    def _extract_theme_colors(self):
        main_img = self.bitmaps.get('main')
        
        # 1. Accurately sample the chassis background from the bottom bezel
        if main_img and not main_img.isNull():
            w = main_img.width()
            h = main_img.height()
            
            # Sample multiple points on the bottom chassis bezel
            sample_points = [
                (int(w * 0.4), min(h - 8, 108)),
                (int(w * 0.6), min(h - 8, 108)),
                (int(w * 0.8), min(h - 8, 108)),
                (int(w * 0.9), min(h - 8, 108)),
                (20, min(h - 8, 108))
            ]
            samples = [main_img.pixelColor(x, y) for x, y in sample_points]
            avg_r = int(sum(c.red() for c in samples) / len(samples))
            avg_g = int(sum(c.green() for c in samples) / len(samples))
            avg_b = int(sum(c.blue() for c in samples) / len(samples))
            
            chassis_col = QColor(avg_r, avg_g, avg_b)
            self.colors['chassis_bg'] = chassis_col.name()
            
            # Dynamic contrast detection (Luminance)
            luminance = (0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b)
            if luminance > 125:
                # Light/Silver/Aluminum Skin
                self.colors['chassis_border'] = chassis_col.darker(140).name()
                self.colors['panel_bg'] = chassis_col.darker(110).name()
                self.colors['button_bg'] = chassis_col.lighter(105).name()
                self.colors['button_border'] = chassis_col.darker(130).name()
                self.colors['button_text'] = "#101218"
                self.colors['titlebar_text'] = "#101218"
            else:
                # Dark/Obsidian/Classic Skin
                self.colors['chassis_border'] = chassis_col.lighter(130).name()
                self.colors['panel_bg'] = chassis_col.darker(150).name()
                self.colors['button_bg'] = chassis_col.lighter(115).name()
                self.colors['button_border'] = chassis_col.lighter(130).name()
                self.colors['button_text'] = "#d4d8e8"
                self.colors['titlebar_text'] = "#00e5ff"

            # Sample LCD background from display area (50, 25)
            lcd_sample = main_img.pixelColor(50, 25)
            if 'lcd_bg' not in self.colors:
                self.colors['lcd_bg'] = lcd_sample.name()

        # 2. Visualizer Colors from VISCOLOR.TXT
        if len(self.vis_colors) >= 24:
            self.colors['vis_bg'] = self.vis_colors[0].name()
            self.colors['lcd_bg'] = self.vis_colors[0].name()
            self.colors['vis_peaks'] = self.vis_colors[23].name()
            self.colors['vis_bars_low'] = self.vis_colors[17].name()   # bottom of spec
            self.colors['vis_bars_mid'] = self.vis_colors[10].name()   # middle of spec
            self.colors['vis_bars_high'] = self.vis_colors[2].name()   # top of spec
            self.colors['vis_oscilloscope'] = self.vis_colors[18].name()
            
            # LCD text color from top of spec or bright color
            self.colors['lcd_text'] = self.vis_colors[2].name()
            self.colors['lcd_text_dim'] = self.vis_colors[0].lighter(140).name()
            self.colors['lcd_kbps'] = self.vis_colors[11].name()

        # 3. Smart Playlist Color Derivations
        if 'playlist_bg' in self.colors and 'playlist_playing_bg' not in self.colors:
            if 'playlist_selected_bg' in self.colors:
                self.colors['playlist_playing_bg'] = self.colors['playlist_selected_bg']
            else:
                self.colors['playlist_playing_bg'] = QColor(self.colors['playlist_bg']).lighter(130).name()

        # 4. Fallbacks
        defaults = {
            "chassis_bg": "#282932",
            "chassis_border": "#4e5062",
            "panel_bg": "#000000",
            "titlebar_bg": "#1c1d24",
            "titlebar_text": "#00e5ff",
            "lcd_bg": "#020902",
            "lcd_text": "#00ff33",
            "lcd_text_dim": "#003b0c",
            "lcd_kbps": "#00dd22",
            "vis_bg": "#000000",
            "vis_bars_low": "#00ff44",
            "vis_bars_mid": "#ffea00",
            "vis_bars_high": "#ff2200",
            "vis_peaks": "#ffffff",
            "vis_oscilloscope": "#00ff66",
            "button_bg": "#323440",
            "button_border": "#4e5062",
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
        for k, v in defaults.items():
            if k not in self.colors:
                self.colors[k] = v
