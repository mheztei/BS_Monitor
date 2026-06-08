"""
BS Monitor — Базалық станциялар мониторингі
Kivy 2.3 + KivyMD 1.2 + plyer (нативная камера Android)
"""
import math
import datetime
import os
import threading

from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.clock import Clock, mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.utils import get_color_from_hex as hx
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.menu import MDDropdownMenu

try:
    from plyer import camera as plyer_cam
    CAMERA_OK = True
except Exception:
    CAMERA_OK = False

try:
    from plyer import gps as plyer_gps
    GPS_OK = True
except Exception:
    GPS_OK = False

# =============================================================================
# ДАННЫЕ
# =============================================================================

USERS = {"Diyara": "123", "admin": "admin"}

STATIONS = [
    {"id": "БС-АЛМ-014", "stage": "Іске қосу",       "distance": "0,8 км",
     "color": "#FFC107", "progress": 80,  "lat": 43.2560, "lng": 76.9286},
    {"id": "БС-АЛМ-031", "stage": "Антенна орнату",  "distance": "1,2 км",
     "color": "#E53935", "progress": 45,  "lat": 43.2380, "lng": 76.9120},
    {"id": "БС-АЛМ-027", "stage": "Тірек құрылысы",  "distance": "1,5 км",
     "color": "#FFC107", "progress": 30,  "lat": 43.2210, "lng": 76.9510},
    {"id": "БС-АЛМ-018", "stage": "Аяқталды",        "distance": "2,1 км",
     "color": "#43A047", "progress": 95,  "lat": 43.2680, "lng": 76.9450},
    {"id": "БС-АЛМ-009", "stage": "Аяқталды",        "distance": "3,4 км",
     "color": "#43A047", "progress": 100, "lat": 43.2300, "lng": 76.8950},
]

STAGE_MATERIALS = {
    "Алаңды дайындау": [
        {"name": "Бетон қоспасы М300", "unit": "м³",   "need": 4,  "stock": 12},
        {"name": "Арматура 12 мм",     "unit": "м",    "need": 60, "stock": 200},
        {"name": "Геотекстиль",         "unit": "м²",   "need": 25, "stock": 0},
    ],
    "Тірек құрылысы": [
        {"name": "Болат діңгек 30 м",   "unit": "дана", "need": 1,  "stock": 3},
        {"name": "Анкерлік болт М24",   "unit": "дана", "need": 16, "stock": 40},
        {"name": "Жерге қосу шинасы",   "unit": "м",    "need": 20, "stock": 8},
    ],
    "Антенна орнату": [
        {"name": "Антенна T2002M6",     "unit": "дана", "need": 3,  "stock": 5},
        {"name": "Монтаждық кронштейн", "unit": "дана", "need": 3,  "stock": 6},
        {"name": "Клэмп 7/8",           "unit": "дана", "need": 12, "stock": 4},
    ],
    "Кабель төсеу": [
        {"name": "Фидер 7/8 коаксиал",  "unit": "м",    "need": 80, "stock": 150},
        {"name": "Коннектор 7/8",       "unit": "дана", "need": 6,  "stock": 10},
        {"name": "Жерге қосу жинағы",   "unit": "дана", "need": 4,  "stock": 2},
    ],
    "Іске қосу-баптау": [
        {"name": "RRU модулі",           "unit": "дана", "need": 3,  "stock": 4},
        {"name": "Қуат кабелі",          "unit": "м",    "need": 30, "stock": 60},
        {"name": "Оптикалық патч-корд",  "unit": "дана", "need": 6,  "stock": 0},
    ],
}

STAGES   = list(STAGE_MATERIALS.keys())
STATUSES = ["Орындалуда", "Аяқталды", "Тексеруде", "Ақаулар анықталды"]
STATUS_COLOR = {
    "Орындалуда":        "#FFC107",
    "Аяқталды":          "#43A047",
    "Тексеруде":         "#FFC107",
    "Ақаулар анықталды": "#E53935",
}

FOOTER = "Магистрант Муттахиден Дияра · АУЭС, 2025"

# Цвета
C_RED      = hx("#C62828")
C_RED_DARK = hx("#8B1F1F")
C_RED_L    = hx("#FCE4E4")
C_INK      = hx("#1F2937")
C_INK2     = hx("#4B5563")
C_MUTED    = hx("#9CA3AF")
C_BG       = hx("#F8F9FB")
C_LINE     = hx("#E5E7EB")
C_GREEN    = hx("#43A047")
C_YELLOW   = hx("#FFC107")


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ВИДЖЕТЫ
# =============================================================================

def get_app():
    return MDApp.get_running_app()


def snack(text, ok=False):
    s = Snackbar(text=text, snackbar_x="10dp", snackbar_y="10dp")
    s.size_hint_x = 0.95
    s.bg_color = [0.18, 0.63, 0.28, 1] if ok else [0.77, 0.16, 0.16, 1]
    s.open()


def go(name):
    get_app().root.current = name


class RedBox(BoxLayout):
    """Виджет с красным фоном — используется как шапка."""
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*C_RED_DARK)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *_):
        self._rect.pos  = self.pos
        self._rect.size = self.size


class ColorBox(BoxLayout):
    """Виджет с произвольным цветом фона."""
    def __init__(self, color, **kw):
        super().__init__(**kw)
        self._color = color
        with self.canvas.before:
            self._ci = Color(*color)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *_):
        self._rect.pos  = self.pos
        self._rect.size = self.size


def white_label(text, size=14, bold=False, color=None, halign="left"):
    return MDLabel(
        text=text,
        font_size=sp(size),
        bold=bold,
        theme_text_color="Custom",
        text_color=color or [1, 1, 1, 1],
        halign=halign,
        size_hint_y=None,
        height=dp(28),
    )


def ink_label(text, size=13, bold=False, color=None, halign="left", height=28):
    return MDLabel(
        text=text,
        font_size=sp(size),
        bold=bold,
        theme_text_color="Custom",
        text_color=color or C_INK,
        halign=halign,
        size_hint_y=None,
        height=dp(height),
    )


def spacer(h=10):
    return Widget(size_hint_y=None, height=dp(h))


def make_header(title, subtitle=None, back_screen=None, right_buttons=None):
    """Красная шапка с кнопкой назад."""
    box = RedBox(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(72),
        padding=[dp(4), dp(10), dp(8), dp(8)],
        spacing=dp(2),
    )
    if back_screen:
        btn = MDIconButton(
            icon="arrow-left",
            theme_icon_color="Custom",
            icon_color=[1, 1, 1, 1],
        )
        btn.bind(on_release=lambda *_: go(back_screen))
        box.add_widget(btn)

    title_col = BoxLayout(orientation="vertical", spacing=0)
    title_col.add_widget(white_label(title, size=17, bold=True))
    if subtitle:
        title_col.add_widget(white_label(subtitle, size=11,
                                         color=[1, 0.8, 0.8, 1]))
    box.add_widget(title_col)

    if right_buttons:
        for icon, cb in right_buttons:
            btn = MDIconButton(
                icon=icon,
                theme_icon_color="Custom",
                icon_color=[1, 1, 1, 1],
            )
            btn.bind(on_release=cb)
            box.add_widget(btn)

    return box


def footer():
    lbl = MDLabel(
        text=FOOTER,
        font_size=sp(10),
        italic=True,
        halign="center",
        theme_text_color="Custom",
        text_color=C_MUTED,
        size_hint_y=None,
        height=dp(28),
    )
    return lbl


def red_button(text, icon, on_press, height=50):
    box = ColorBox(
        color=C_RED,
        size_hint_y=None,
        height=dp(height),
        orientation="horizontal",
        padding=[dp(12), dp(8)],
        spacing=dp(8),
    )
    box.add_widget(MDIconButton(
        icon=icon, theme_icon_color="Custom",
        icon_color=[1, 1, 1, 1],
        size_hint=(None, None), size=(dp(32), dp(32)),
        pos_hint={"center_y": 0.5},
    ))
    lbl = MDLabel(
        text=text, font_size=sp(14), bold=True,
        theme_text_color="Custom", text_color=[1, 1, 1, 1],
        halign="left",
    )
    box.add_widget(lbl)
    from kivy.uix.behaviors import ButtonBehavior
    # Обёртка для on_press
    from kivy.uix.button import Button
    box.bind(on_touch_down=lambda w, t: on_press() if w.collide_point(*t.pos) else None)
    return box


# =============================================================================
# ЭКРАН 1: ВХОД
# =============================================================================

class LoginScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="login", **kw)
        self._build_ui()

    def _build_ui(self):
        with self.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        root = BoxLayout(orientation="vertical")

        scroll = ScrollView(do_scroll_x=False)
        col = BoxLayout(
            orientation="vertical",
            padding=[dp(24), dp(32), dp(24), dp(16)],
            spacing=dp(10),
            size_hint_y=None,
        )
        col.bind(minimum_height=col.setter("height"))

        # Логотип
        logo_wrap = FloatLayout(size_hint_y=None, height=dp(140))
        logo_w = Widget(
            size_hint=(None, None), size=(dp(120), dp(120)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        with logo_w.canvas:
            Color(*C_RED)
            Ellipse(pos=(dp(0), dp(0)), size=(dp(120), dp(120)))
        logo_lbl = MDLabel(
            text="BS", font_size=sp(44), bold=True,
            theme_text_color="Custom", text_color=[1, 1, 1, 1],
            halign="center", valign="middle",
            size_hint=(None, None), size=(dp(120), dp(120)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        logo_wrap.add_widget(logo_w)
        logo_wrap.add_widget(logo_lbl)
        col.add_widget(logo_wrap)

        col.add_widget(ink_label("BS Monitor", size=26, bold=True,
                                  halign="center", height=40))
        col.add_widget(ink_label("Базалық станциялар мониторингі",
                                  size=13, halign="center",
                                  color=C_MUTED, height=28))
        col.add_widget(spacer(20))

        self.f_login = MDTextField(
            hint_text="Логин",
            icon_right="account-outline",
            size_hint_x=0.88,
            pos_hint={"center_x": 0.5},
        )
        col.add_widget(self.f_login)

        self.f_pass = MDTextField(
            hint_text="Құпия сөз",
            icon_right="lock-outline",
            password=True,
            size_hint_x=0.88,
            pos_hint={"center_x": 0.5},
        )
        col.add_widget(self.f_pass)

        self.err_lbl = MDLabel(
            text="", font_size=sp(12),
            theme_text_color="Custom", text_color=C_RED,
            halign="center", size_hint_y=None, height=dp(24),
        )
        col.add_widget(self.err_lbl)

        btn = MDRaisedButton(
            text="Кіру",
            md_bg_color=C_RED,
            size_hint=(0.88, None), height=dp(52),
            pos_hint={"center_x": 0.5},
        )
        btn.bind(on_release=self.try_login)
        col.add_widget(btn)

        col.add_widget(spacer(16))
        col.add_widget(footer())
        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)

    def try_login(self, *_):
        login = self.f_login.text.strip()
        pwd   = self.f_pass.text.strip()
        if not login or not pwd:
            self.err_lbl.text = "Барлық өрістерді толтырыңыз"
            return
        if USERS.get(login) == pwd:
            self.err_lbl.text = ""
            go("stations")
        else:
            self.err_lbl.text = "Логин немесе құпия сөз қате"


# =============================================================================
# ЭКРАН 2: СПИСОК СТАНЦИЙ
# =============================================================================

class StationsScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="stations", **kw)
        self._stations = STATIONS
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        header = make_header(
            "БС нысандары",
            right_buttons=[
                ("map-outline", lambda *_: go("map")),
                ("chart-bar",   lambda *_: go("monitoring")),
            ],
        )
        root.add_widget(header)

        # Поиск
        search_box = BoxLayout(
            size_hint_y=None, height=dp(56),
            padding=[dp(12), dp(6)],
        )
        self.search = MDTextField(
            hint_text="Іздеу...",
            icon_right="magnify",
        )
        self.search.bind(text=self.on_search)
        search_box.add_widget(self.search)
        root.add_widget(search_box)

        # Список
        self.scroll = ScrollView(do_scroll_x=False)
        self.list_col = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=[dp(10), dp(4)],
            size_hint_y=None,
        )
        self.list_col.bind(minimum_height=self.list_col.setter("height"))
        self._fill_list(STATIONS)
        self.scroll.add_widget(self.list_col)
        root.add_widget(self.scroll)

        root.add_widget(footer())
        self.add_widget(root)

    def _fill_list(self, stations):
        self.list_col.clear_widgets()
        for s in stations:
            self.list_col.add_widget(self._make_card(s))

    def _make_card(self, s):
        card = MDCard(
            orientation="horizontal",
            size_hint_y=None, height=dp(70),
            elevation=2,
            padding=[dp(10), dp(8)],
            spacing=dp(8),
        )

        # Цветная полоса
        strip = Widget(size_hint=(None, 1), width=dp(6))
        with strip.canvas:
            Color(*hx(s["color"]))
            RoundedRectangle(pos=strip.pos, size=strip.size, radius=[dp(3)])
        strip.bind(pos=lambda w, *_: self._upd_strip(w, s["color"]),
                   size=lambda w, *_: self._upd_strip(w, s["color"]))
        card.add_widget(strip)

        # Текст
        txt_col = BoxLayout(orientation="vertical", spacing=0)
        txt_col.add_widget(MDLabel(
            text=s["id"], font_size=sp(14), bold=True,
            theme_text_color="Custom", text_color=C_INK,
        ))
        txt_col.add_widget(MDLabel(
            text=f"{s['stage']} · {s['distance']}",
            font_size=sp(12),
            theme_text_color="Custom", text_color=C_MUTED,
        ))
        card.add_widget(txt_col)

        # Кнопка открыть карточку
        btn = MDIconButton(
            icon="chevron-right",
            theme_icon_color="Custom", icon_color=C_INK2,
        )
        station = s
        btn.bind(on_release=lambda *_: self._open(station))
        card.add_widget(btn)

        card.bind(on_touch_down=lambda w, t: self._open(station)
                  if w.collide_point(*t.pos) else None)
        return card

    def _upd_strip(self, w, color):
        w.canvas.clear()
        with w.canvas:
            Color(*hx(color))
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(3)])

    def _open(self, station):
        get_app().current_station = station
        go("register")

    def on_search(self, _, text):
        q = text.lower().strip()
        filtered = [s for s in STATIONS
                    if not q or q in s["id"].lower() or q in s["stage"].lower()]
        self._fill_list(filtered)


# =============================================================================
# ЭКРАН 3: РЕГИСТРАЦИЯ (КАМЕРА + GPS)
# =============================================================================

class RegisterScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="register", **kw)
        self._photo_taken = False
        self._photo_path  = None
        self._stage_val   = STAGES[2]
        self._status_val  = STATUSES[1]
        self._build_ui()

    def on_enter(self, *_):
        """Вызывается при открытии экрана."""
        s = get_app().current_station
        self.header.clear_widgets()
        self.header.add_widget(make_header(
            "Кезеңді тіркеу",
            subtitle=s["id"] if s else "",
            back_screen="stations",
        ))
        self._photo_taken = False
        self._photo_path  = None
        self._reset_photo_display()
        self._get_gps(s)

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        # Заглушка шапки — заполняется в on_enter
        self.header = BoxLayout(size_hint_y=None, height=dp(72))
        root.add_widget(self.header)

        scroll = ScrollView(do_scroll_x=False)
        col = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(8)],
            spacing=dp(10),
            size_hint_y=None,
        )
        col.bind(minimum_height=col.setter("height"))

        # ── Область фото ──────────────────────────────────────────────────
        self.photo_area = ColorBox(
            color=hx("#F1F3F5"),
            size_hint_y=None, height=dp(200),
            orientation="vertical",
            padding=dp(12),
        )
        self._reset_photo_display()
        col.add_widget(self.photo_area)

        # ── Кнопка камеры ─────────────────────────────────────────────────
        cam_btn = MDRaisedButton(
            text="  Камераны ашу",
            icon="camera",
            md_bg_color=C_RED,
            size_hint=(1, None), height=dp(48),
        )
        cam_btn.bind(on_release=self.take_photo)
        col.add_widget(cam_btn)

        # ── GPS ───────────────────────────────────────────────────────────
        gps_card = ColorBox(
            color=hx("#E3F2FD"),
            size_hint_y=None, height=dp(64),
            orientation="horizontal",
            padding=[dp(12), dp(8)],
            spacing=dp(8),
        )
        self.gps_label = MDLabel(
            text="GPS: іздеу...",
            font_size=sp(13), bold=True,
            theme_text_color="Custom",
            text_color=hx("#1565C0"),
        )
        gps_refresh = MDIconButton(
            icon="refresh",
            theme_icon_color="Custom",
            icon_color=hx("#1565C0"),
            size_hint=(None, None), size=(dp(40), dp(40)),
        )
        gps_refresh.bind(on_release=lambda *_: self._get_gps(get_app().current_station))
        gps_card.add_widget(MDIconButton(
            icon="crosshairs-gps",
            theme_icon_color="Custom", icon_color=hx("#1565C0"),
            size_hint=(None, None), size=(dp(40), dp(40)),
        ))
        gps_card.add_widget(self.gps_label)
        gps_card.add_widget(gps_refresh)
        col.add_widget(gps_card)

        # ── Этап ──────────────────────────────────────────────────────────
        self.stage_field = MDTextField(
            hint_text="Кезең",
            text=self._stage_val,
            icon_right="menu-down",
        )
        self.stage_field.bind(focus=self._open_stage_menu)
        col.add_widget(self.stage_field)

        # ── Статус ────────────────────────────────────────────────────────
        self.status_field = MDTextField(
            hint_text="Статус",
            text=self._status_val,
            icon_right="menu-down",
        )
        self.status_field.bind(focus=self._open_status_menu)
        col.add_widget(self.status_field)

        col.add_widget(spacer(8))

        # ── Отправить ─────────────────────────────────────────────────────
        send_btn = MDRaisedButton(
            text="  Серверге жіберу",
            icon="cloud-upload",
            md_bg_color=C_RED,
            size_hint=(1, None), height=dp(52),
        )
        send_btn.bind(on_release=self.send)
        col.add_widget(send_btn)

        col.add_widget(spacer(8))

        # ── Калькулятор ───────────────────────────────────────────────────
        calc_btn = MDRaisedButton(
            text="  Радио қамту есебі",
            icon="calculator",
            md_bg_color=[1, 1, 1, 1],
            text_color=C_RED,
            size_hint=(1, None), height=dp(46),
        )
        calc_btn.bind(on_release=lambda *_: go("calculator"))
        col.add_widget(calc_btn)

        # ── Склад ─────────────────────────────────────────────────────────
        wh_btn = MDRaisedButton(
            text="  Материалдар қоймасы",
            icon="package-variant",
            md_bg_color=[1, 1, 1, 1],
            text_color=C_RED,
            size_hint=(1, None), height=dp(46),
        )
        wh_btn.bind(on_release=lambda *_: go("warehouse"))
        col.add_widget(wh_btn)

        col.add_widget(spacer(8))
        col.add_widget(footer())

        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)

    def _reset_photo_display(self):
        self.photo_area.clear_widgets()
        icon = MDIconButton(
            icon="camera-outline",
            theme_icon_color="Custom", icon_color=C_MUTED,
            icon_size="56sp",
            pos_hint={"center_x": 0.5},
        )
        lbl1 = ink_label("Сурет жоқ", halign="center", color=C_MUTED)
        lbl2 = ink_label("«Камераны ашу» батырмасын басыңыз",
                          size=11, halign="center", color=C_MUTED)
        self.photo_area.add_widget(icon)
        self.photo_area.add_widget(lbl1)
        self.photo_area.add_widget(lbl2)

    def take_photo(self, *_):
        """Открывает нативную камеру Android через plyer."""
        if not CAMERA_OK:
            # Симуляция для десктопа
            self._on_photo_done("simulated_photo.jpg")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        s  = get_app().current_station
        sid = s["id"].replace("-", "") if s else "BS"
        filename = f"/sdcard/Pictures/BSMonitor_{sid}_{ts}.jpg"
        try:
            plyer_cam.take_picture(
                filename=filename,
                on_complete=self._on_photo_done,
            )
        except Exception as e:
            snack(f"Камера қатесі: {e}")

    @mainthread
    def _on_photo_done(self, path):
        if not path:
            snack("Сурет алынбады")
            return
        self._photo_path  = path
        self._photo_taken = True

        self.photo_area.clear_widgets()

        icon = MDIconButton(
            icon="check-circle",
            theme_icon_color="Custom",
            icon_color=hx("#43A047"),
            icon_size="56sp",
            pos_hint={"center_x": 0.5},
        )
        self.photo_area.add_widget(icon)
        self.photo_area.add_widget(ink_label(
            "Сурет сақталды", bold=True, halign="center",
            color=hx("#2E7D32"),
        ))
        fname = os.path.basename(str(path))
        self.photo_area.add_widget(ink_label(
            fname, size=10, halign="center", color=C_MUTED,
        ))
        # Меняем фон на зелёный
        self.photo_area.canvas.before.clear()
        with self.photo_area.canvas.before:
            Color(*hx("#E8F5E9"))
            Rectangle(pos=self.photo_area.pos, size=self.photo_area.size)

        snack("Сурет сақталды ✓", ok=True)

    def _get_gps(self, station):
        self.gps_label.text = "GPS: іздеу..."
        if GPS_OK:
            def _start():
                try:
                    plyer_gps.configure(
                        on_location=self._on_location,
                        on_status=None,
                    )
                    plyer_gps.start(minTime=1000, minDistance=0)
                except Exception:
                    self._fallback_gps(station)
            threading.Thread(target=_start, daemon=True).start()
        else:
            self._fallback_gps(station)

    @mainthread
    def _on_location(self, **kwargs):
        lat = kwargs.get("lat", 0)
        lon = kwargs.get("lon", 0)
        acc = kwargs.get("accuracy", None)
        self.gps_label.text = f"GPS: {lat:.4f}° N, {lon:.4f}° E"
        if acc:
            self.gps_label.text += f" ±{acc:.0f}м"
        try:
            plyer_gps.stop()
        except Exception:
            pass

    @mainthread
    def _fallback_gps(self, station):
        if station:
            self.gps_label.text = (
                f"GPS: {station['lat']:.4f}° N, {station['lng']:.4f}° E"
            )
        else:
            self.gps_label.text = "GPS: қол жетімді емес"

    def _open_stage_menu(self, field, focused):
        if not focused:
            return
        items = [
            {"text": s, "viewclass": "OneLineListItem",
             "on_release": lambda x=s: self._set_stage(x)}
            for s in STAGES
        ]
        MDDropdownMenu(caller=field, items=items, width_mult=4).open()

    def _set_stage(self, val):
        self._stage_val = val
        self.stage_field.text = val

    def _open_status_menu(self, field, focused):
        if not focused:
            return
        items = [
            {"text": s, "viewclass": "OneLineListItem",
             "on_release": lambda x=s: self._set_status(x)}
            for s in STATUSES
        ]
        MDDropdownMenu(caller=field, items=items, width_mult=4).open()

    def _set_status(self, val):
        self._status_val = val
        self.status_field.text = val

    def send(self, *_):
        if not self._photo_taken:
            snack("Алдымен сурет түсіріңіз")
            return
        s = get_app().current_station
        if s:
            s["stage"]    = self._stage_val
            s["color"]    = STATUS_COLOR.get(self._status_val, s["color"])
            if self._status_val == "Аяқталды":
                s["progress"] = 100
        snack(f"{s['id']}: серверге жіберілді ✓", ok=True)


# =============================================================================
# ЭКРАН 4: КАЛЬКУЛЯТОР ОКАМУРА–ХАТА
# =============================================================================

class ChartWidget(Widget):
    """Canvas-график зависимости d(h_b)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._points = []
        self._current_hb = 35
        self.size_hint_y = None
        self.height = dp(220)
        self.bind(size=self._draw, pos=self._draw)

    def set_data(self, points, current_hb):
        self._points  = points
        self._current_hb = current_hb
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        if not self._points:
            return

        W, H = self.width, self.height
        pl, pr, pt, pb = dp(42), dp(12), dp(18), dp(30)
        pw, ph = W - pl - pr, H - pt - pb

        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]
        x0, x1 = min(xs), max(xs)
        y0, y1 = 0, max(ys) * 1.15

        def to_px(x, y):
            px = self.x + pl + (x - x0) / max(x1 - x0, 0.001) * pw
            py = self.y + pb + (y - y0) / max(y1 - y0, 0.001) * ph
            return px, py

        with self.canvas:
            # Фон
            Color(0.98, 0.98, 0.99, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])

            # Сетка
            Color(*C_LINE)
            for i in range(5):
                gy = self.y + pb + ph * i / 4
                Line(points=[self.x + pl, gy, self.x + W - pr, gy], width=1)

            # Линия графика
            Color(*C_RED)
            pts_flat = []
            for p in self._points:
                px, py = to_px(*p)
                pts_flat += [px, py]
            if len(pts_flat) >= 4:
                Line(points=pts_flat, width=dp(2.5))

            # Точки
            for x, y in self._points:
                px, py = to_px(x, y)
                is_cur = abs(x - self._current_hb) < 3
                r = dp(6) if is_cur else dp(4)
                Color(1, 1, 1, 1)
                Ellipse(pos=(px - r, py - r), size=(r * 2, r * 2))
                Color(*C_RED)
                Line(circle=(px, py, r), width=dp(2))


class CalculatorScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="calculator", **kw)
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")
        root.add_widget(make_header("Радио қамту есебі", back_screen="stations"))

        scroll = ScrollView(do_scroll_x=False)
        col = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(10)],
            spacing=dp(10),
            size_hint_y=None,
        )
        col.bind(minimum_height=col.setter("height"))

        # Формула
        formula_box = ColorBox(
            color=hx("#FCE4E4"),
            size_hint_y=None, height=dp(72),
            orientation="vertical",
            padding=[dp(12), dp(8)],
        )
        formula_box.add_widget(ink_label(
            "Окамура–Хата моделі (қалалық орта)",
            size=11, color=C_MUTED, halign="center",
        ))
        formula_box.add_widget(ink_label(
            "L = 69.55 + 26.16·log f − 13.82·log h_b − a(h_m) + (44.9−6.55·log h_b)·log d",
            size=10, bold=True, halign="center", color=C_INK,
        ))
        col.add_widget(formula_box)

        self.f_freq = MDTextField(hint_text="Жиілік f, МГц",  text="900")
        self.f_hb   = MDTextField(hint_text="Антенна биіктігі h_b, м", text="35")
        self.f_hm   = MDTextField(hint_text="Мобильді антенна h_m, м", text="1.5")
        self.f_loss = MDTextField(hint_text="Рұқсат етілген жоғалу L, дБ", text="140")
        for f in [self.f_freq, self.f_hb, self.f_hm, self.f_loss]:
            f.input_filter = "float"
            col.add_widget(f)

        calc_btn = MDRaisedButton(
            text="Есептеу", md_bg_color=C_RED,
            size_hint=(1, None), height=dp(50),
        )
        calc_btn.bind(on_release=self.calculate)
        col.add_widget(calc_btn)

        # Результат
        result_box = ColorBox(
            color=hx("#FCE4E4"),
            size_hint_y=None, height=dp(100),
            orientation="vertical",
            padding=[dp(12), dp(8)],
        )
        result_box.add_widget(ink_label(
            "Максималды қамту радиусы", size=12, halign="center", color=C_MUTED,
        ))
        self.result_lbl = MDLabel(
            text="—", font_size=sp(40), bold=True,
            theme_text_color="Custom", text_color=C_RED,
            halign="center",
        )
        result_box.add_widget(self.result_lbl)
        self.detail_lbl = ink_label("", size=11, halign="center", color=C_MUTED)
        result_box.add_widget(self.detail_lbl)
        col.add_widget(result_box)

        # График
        chart_card = ColorBox(
            color=[1, 1, 1, 1],
            size_hint_y=None, height=dp(240),
            orientation="vertical",
            padding=[dp(8), dp(8)],
        )
        chart_card.add_widget(ink_label(
            "График: d(h_b)", size=12, bold=True, color=C_INK,
        ))
        self.chart = ChartWidget()
        chart_card.add_widget(self.chart)
        col.add_widget(chart_card)

        # Таблица
        self.table_col = BoxLayout(
            orientation="vertical", spacing=dp(4),
            size_hint_y=None,
        )
        self.table_col.bind(minimum_height=self.table_col.setter("height"))
        col.add_widget(self.table_col)

        col.add_widget(footer())
        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)

    def calculate(self, *_):
        try:
            f  = float(self.f_freq.text or 900)
            hb = float(self.f_hb.text or 35)
            hm = float(self.f_hm.text or 1.5)
            L  = float(self.f_loss.text or 140)
        except ValueError:
            snack("Барлық өрістерге сан енгізіңіз")
            return

        def hata(F, HB, HM, LL):
            ahm = (1.1 * math.log10(F) - 0.7) * HM - (1.56 * math.log10(F) - 0.8)
            A   = 69.55 + 26.16 * math.log10(F) - 13.82 * math.log10(HB) - ahm
            B   = 44.9 - 6.55 * math.log10(HB)
            return ahm, A, 10 ** ((LL - A) / B)

        ahm, A, d = hata(f, hb, hm, L)
        self.result_lbl.text  = f"{d:.2f} км"
        self.detail_lbl.text  = f"a(h_m)={ahm:.3f} дБ  ·  A={A:.2f} дБ  ·  f={f:.0f} МГц"

        points = [(h, hata(f, h, hm, L)[2]) for h in [20, 30, 40, 50, 60]]
        self.chart.set_data(points, hb)

        self.table_col.clear_widgets()
        for h, dd in points:
            is_cur = abs(h - hb) < 3
            row = ColorBox(
                color=hx("#FCE4E4") if is_cur else [1, 1, 1, 1],
                size_hint_y=None, height=dp(36),
                orientation="horizontal",
                padding=[dp(10), dp(4)],
            )
            row.add_widget(ink_label(
                f"h_b = {h} м", bold=is_cur, color=C_INK,
            ))
            row.add_widget(ink_label(
                f"d = {dd:.2f} км", bold=True,
                color=C_RED if is_cur else C_INK2,
                halign="right",
            ))
            self.table_col.add_widget(row)


# =============================================================================
# ЭКРАН 5: МОНИТОРИНГ
# =============================================================================

class MonitoringScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="monitoring", **kw)
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")
        root.add_widget(make_header("Мониторинг", back_screen="stations"))

        scroll = ScrollView(do_scroll_x=False)
        col = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(10)],
            spacing=dp(12),
            size_hint_y=None,
        )
        col.bind(minimum_height=col.setter("height"))

        total = len(STATIONS)
        done  = sum(1 for s in STATIONS if s["progress"] == 100)
        inpro = sum(1 for s in STATIONS if 0 < s["progress"] < 100)
        avg   = round(sum(s["progress"] for s in STATIONS) / total)

        # Стат карточки
        stat_row = BoxLayout(size_hint_y=None, height=dp(90), spacing=dp(8))
        for num, lbl, color, bg in [
            (done,  "Аяқталды",   "#43A047", "#E8F5E9"),
            (inpro, "Орындалуда", "#F57C00", "#FFF3E0"),
            (total, "Барлығы",    "#C62828", "#FCE4E4"),
        ]:
            card = ColorBox(
                color=hx(bg),
                orientation="vertical",
                padding=[dp(8), dp(8)],
            )
            card.add_widget(MDLabel(
                text=str(num), font_size=sp(30), bold=True,
                theme_text_color="Custom", text_color=hx(color),
                halign="center",
            ))
            card.add_widget(ink_label(lbl, size=11, halign="center", color=C_INK2))
            stat_row.add_widget(card)
        col.add_widget(stat_row)

        # Средний прогресс
        col.add_widget(ink_label(f"Орташа орындалу: {avg}%", bold=True, color=C_INK))
        bar = MDProgressBar(value=avg, max=100, color=C_RED,
                            size_hint_y=None, height=dp(10))
        col.add_widget(bar)

        col.add_widget(spacer(8))
        col.add_widget(ink_label("Нысандар бойынша орындалу",
                                  size=15, bold=True, color=C_INK))

        # Прогресс по станциям
        for s in STATIONS:
            pct = s["progress"]
            bar_color = hx("#43A047") if pct == 100 else (
                hx("#F57C00") if pct >= 50 else hx("#E53935"))
            card = ColorBox(
                color=[1, 1, 1, 1],
                size_hint_y=None, height=dp(76),
                orientation="vertical",
                padding=[dp(12), dp(8)],
                spacing=dp(4),
            )
            row = BoxLayout(size_hint_y=None, height=dp(22))
            row.add_widget(ink_label(s["id"], bold=True, color=C_INK))
            row.add_widget(ink_label(f"{pct}%", bold=True,
                                      halign="right",
                                      color=list(bar_color)))
            card.add_widget(row)
            pb = MDProgressBar(value=pct, max=100,
                               color=bar_color,
                               size_hint_y=None, height=dp(8))
            card.add_widget(pb)
            card.add_widget(ink_label(s["stage"], size=11, color=C_MUTED))
            col.add_widget(card)

        # Эффективность
        eff_box = ColorBox(
            color=hx("#E3F2FD"),
            size_hint_y=None, height=dp(110),
            orientation="vertical",
            padding=[dp(14), dp(10)],
        )
        eff_box.add_widget(ink_label(
            "Цифрлық мониторингтің тиімділігі",
            size=13, bold=True, color=hx("#1565C0"),
        ))
        eff_row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(8))
        for val, lbl in [("−18%", "құрылыс ұзақтығы"),
                         ("−25%", "ақаулар саны")]:
            c = BoxLayout(orientation="vertical")
            c.add_widget(MDLabel(
                text=val, font_size=sp(28), bold=True,
                theme_text_color="Custom", text_color=hx("#1565C0"),
                halign="center",
            ))
            c.add_widget(ink_label(lbl, size=11, halign="center", color=C_INK2))
            eff_row.add_widget(c)
        eff_box.add_widget(eff_row)
        col.add_widget(eff_box)

        col.add_widget(footer())
        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)


# =============================================================================
# ЭКРАН 6: КАРТА
# =============================================================================

class MapCanvas(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint_y = None
        self.height = dp(320)
        self.bind(size=self._draw, pos=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        lats = [s["lat"] for s in STATIONS]
        lngs = [s["lng"] for s in STATIONS]
        lat0, lat1 = min(lats) - 0.008, max(lats) + 0.008
        lng0, lng1 = min(lngs) - 0.008, max(lngs) + 0.008
        W, H = self.width, self.height

        def to_px(lat, lng):
            x = self.x + (lng - lng0) / (lng1 - lng0) * W
            y = self.y + (lat1 - lat) / (lat1 - lat0) * H
            return x, y

        with self.canvas:
            # Фон
            Color(0.94, 0.96, 0.97, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])

            # Сетка
            Color(*C_LINE)
            for i in range(1, 6):
                gx = self.x + W / 6 * i
                Line(points=[gx, self.y, gx, self.y + H], width=1)
                gy = self.y + H / 6 * i
                Line(points=[self.x, gy, self.x + W, gy], width=1)

            # Маркеры
            r = dp(14)
            for s in STATIONS:
                cx, cy = to_px(s["lat"], s["lng"])
                Color(*hx(s["color"]))
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                Color(1, 1, 1, 1)
                Line(circle=(cx, cy, r), width=dp(2))


class MapScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="map", **kw)
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")
        root.add_widget(make_header("БС орналасу картасы", back_screen="stations"))

        scroll = ScrollView(do_scroll_x=False)
        col = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(10)],
            spacing=dp(12),
            size_hint_y=None,
        )
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(ink_label(
            "GPS координаттары бойынша БС-тар орналасуы",
            size=12, color=C_MUTED,
        ))
        col.add_widget(MapCanvas())

        # Легенда
        legend_box = ColorBox(
            color=[1, 1, 1, 1],
            size_hint_y=None, height=dp(110),
            orientation="vertical",
            padding=[dp(12), dp(8)],
            spacing=dp(6),
        )
        legend_box.add_widget(ink_label("Шартты белгілер", bold=True, color=C_INK))
        for color, text in [
            ("#43A047", "Аяқталды / іске қосылды"),
            ("#FFC107", "Орындалу үстінде"),
            ("#E53935", "Назар аудару қажет"),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
            dot = Widget(size_hint=(None, None), size=(dp(14), dp(14)),
                         pos_hint={"center_y": 0.5})
            with dot.canvas:
                Color(*hx(color))
                Ellipse(pos=dot.pos, size=dot.size)
            dot.bind(pos=lambda w, p, c=color: self._upd_dot(w, c),
                     size=lambda w, s, c=color: self._upd_dot(w, c))
            row.add_widget(dot)
            row.add_widget(ink_label(text, size=12, color=C_INK2))
            legend_box.add_widget(row)
        col.add_widget(legend_box)

        col.add_widget(footer())
        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)

    def _upd_dot(self, w, color):
        w.canvas.clear()
        with w.canvas:
            Color(*hx(color))
            Ellipse(pos=w.pos, size=w.size)


# =============================================================================
# ЭКРАН 7: СКЛАД МАТЕРИАЛОВ
# =============================================================================

class WarehouseScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(name="warehouse", **kw)
        self._build_ui()

    def on_enter(self, *_):
        s = get_app().current_station
        stage = s["stage"] if s else STAGES[2]
        self.header.clear_widgets()
        self.header.add_widget(make_header(
            "Материалдар қоймасы",
            subtitle=f"{s['id']} · {stage}" if s else "",
            back_screen="register",
        ))
        self._fill_materials(stage)

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")
        self.header = BoxLayout(size_hint_y=None, height=dp(72))
        root.add_widget(self.header)

        scroll = ScrollView(do_scroll_x=False)
        self.col = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(10)],
            spacing=dp(8),
            size_hint_y=None,
        )
        self.col.bind(minimum_height=self.col.setter("height"))
        scroll.add_widget(self.col)
        root.add_widget(scroll)
        self.add_widget(root)

    def _fill_materials(self, stage):
        self.col.clear_widgets()
        materials = STAGE_MATERIALS.get(stage, STAGE_MATERIALS[STAGES[2]])
        shortage = [m for m in materials if m["stock"] < m["need"]]

        # Сводка
        if shortage:
            bg, color, text = "#FFEBEE", "#E53935", f"{len(shortage)} позиция тапшы"
        else:
            bg, color, text = "#E8F5E9", "#2E7D32", "Барлық материалдар бар"
        summary = ColorBox(
            color=hx(bg), size_hint_y=None, height=dp(50),
            orientation="horizontal", padding=[dp(12), dp(8)], spacing=dp(8),
        )
        summary.add_widget(ink_label(text, bold=True, color=hx(color)))
        self.col.add_widget(summary)

        for m in materials:
            enough = m["stock"] >= m["need"]
            bg_c   = "#E8F5E9" if enough else "#FFEBEE"
            badge  = "Жеткілікті" if enough else "Тапшы"
            b_col  = "#43A047" if enough else "#E53935"

            card = ColorBox(
                color=hx(bg_c) if not enough else [1, 1, 1, 1],
                size_hint_y=None, height=dp(80),
                orientation="vertical",
                padding=[dp(12), dp(8)],
                spacing=dp(4),
            )
            row1 = BoxLayout(size_hint_y=None, height=dp(24))
            row1.add_widget(ink_label(m["name"], bold=True, color=C_INK))
            row1.add_widget(ink_label(badge, bold=True,
                                       halign="right", color=hx(b_col)))
            card.add_widget(row1)

            row2 = BoxLayout(size_hint_y=None, height=dp(20))
            row2.add_widget(ink_label(
                f"Қажет: {m['need']} {m['unit']}", size=12, color=C_INK2,
            ))
            row2.add_widget(ink_label(
                f"Қоймада: {m['stock']} {m['unit']}", size=12,
                bold=True, halign="right", color=hx(b_col),
            ))
            card.add_widget(row2)
            self.col.add_widget(card)

        if shortage:
            order_btn = MDRaisedButton(
                text="  Тапшы материалдарға тапсырыс",
                icon="cart",
                md_bg_color=C_RED,
                size_hint=(1, None), height=dp(48),
            )
            order_btn.bind(on_release=lambda *_: snack(
                f"Тапсырыс жіберілді: {len(shortage)} позиция", ok=True))
            self.col.add_widget(order_btn)

        self.col.add_widget(footer())


# =============================================================================
# ПРИЛОЖЕНИЕ
# =============================================================================

class BSMonitorApp(MDApp):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.current_station = None

    def build(self):
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.primary_hue     = "800"
        self.theme_cls.theme_style     = "Light"
        self.title                     = "BS Monitor"

        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        sm.add_widget(LoginScreen())
        sm.add_widget(StationsScreen())
        sm.add_widget(RegisterScreen())
        sm.add_widget(CalculatorScreen())
        sm.add_widget(MonitoringScreen())
        sm.add_widget(MapScreen())
        sm.add_widget(WarehouseScreen())
        return sm


if __name__ == "__main__":
    BSMonitorApp().run()
