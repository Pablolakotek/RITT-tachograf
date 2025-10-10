# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTabWidget, QSizeGrip
from PySide6.QtCore import QTimer, QSettings
from ritt.ui.effects import install_3d_effects
from ritt.ui.brand import BrandHeader
from ritt.api import NetSignals, NetClient
from ritt.telemetry.factory import build_provider
from ritt.telemetry.service import TelemetryService
from ritt.telemetry.store import TelemetryDB
from ritt.telemetry.mappers.funbit_v9 import normalize_funbit_v9
from ritt.breaks import BreakManager
from ritt.ui.views.main_tab import MainTab
from ritt.ui.views.breaks_tab import BreaksTab
from ritt.ui.views.overlay_tab import OverlayTab
from ritt.ui.dispatcher_tab import DispatcherTab
from .settings_tab import SettingsTab
from .history import HistoryMixin
from .telemetry_loop import TelemetryMixin
from .breaks_control import BreaksMixin
from .overlay_control import OverlayMixin
from ritt.i18n import get_tr, LANGS
from ritt.integrations.events import send_event_to_n8n

class TachographWindow(QMainWindow, HistoryMixin, TelemetryMixin, BreaksMixin, OverlayMixin):
    """Główne okno tachografu RITT PRO"""
    def __init__(self, lang="pl"):
        super().__init__()
        self.lang = lang if lang in LANGS else "pl"
        self.tr = get_tr(self.lang)

        # --- Sieć i telemetria ---
        self.netSignals = NetSignals()
        self.net = NetClient(self.netSignals)
        self.telemetry_service = TelemetryService(
            provider=build_provider(),
            mapper=normalize_funbit_v9,
            db=TelemetryDB("telemetry.sqlite")
        )
        self.breaks = BreakManager()
        self.vehicle_id = "TRUCK_01"
        self.current_job_status = "idle"

        # --- Stan gry / telemetrii ---
        self.engine_on = False
        self.parking_brake = False
        self.speed_kmh = 0.0
        self.driving_seconds = 0
        self.working_seconds = 0
        self.break_seconds = 0
        self.daily_drive_sec = 0
        self.week_drive_sec = 0
        self.fortnight_drive_sec = 0

        # --- UI ---
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(14,10,14,10); root.setSpacing(10)
        self.brand = BrandHeader(); root.addWidget(self.brand, 0)
        self._show_logged_user_on_brand()

        # Top bar
        top_card = QWidget(); top = QHBoxLayout(top_card)
        self.lang_box = QComboBox()
        for code in LANGS: self.lang_box.addItem(code.upper(), code)
        self.lang_box.setCurrentIndex(LANGS.index(self.lang))
        self.lang_box.currentIndexChanged.connect(self.change_lang)
        lbl_lang = QLabel(self.tr["lang"])
        self.ping_btn = QPushButton("🚦 " + self.tr["ping"]); self.ping_btn.setProperty("gold", True)
        self.ping_btn.clicked.connect(self.test_connection)
        top.addWidget(lbl_lang); top.addWidget(self.lang_box); top.addStretch(1); top.addWidget(self.ping_btn)
        root.addWidget(top_card)

        # --- Zakładki ---
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # wszystkie zakładki tworzone od razu, więc historia ma dostęp do breaksTab
        self.mainTab = MainTab(self.tr)
        self.breaksTab = BreaksTab(self)
        self.overlayTab = OverlayTab(self.tr)
        self.dispatcherTab = DispatcherTab(n8n_client=self.net)
        self.settingsTab = SettingsTab(self.tr)

        self.tabs.addTab(self.mainTab, self.tr["tab_main"])
        self.tabs.addTab(self.breaksTab, self.tr["tab_breaks"])
        self.tabs.addTab(self.overlayTab, self.tr["tab_overlay"])
        self.tabs.addTab(self.dispatcherTab, "Dyspozytornia")
        self.tabs.addTab(self.settingsTab, "Ustawienia")
        self.tabs.currentChanged.connect(self._optimize_tab_switch)

        install_3d_effects(self)

        # --- Ustawienia / historia ---
        self.statusBar().addPermanentWidget(QSizeGrip(self))
        self._settings = QSettings("RITT", "Tachograph")
        self._history_file = self._history_path()
        self._history_load()  # ✅ teraz działa, bo breaksTab już istnieje

        # --- Timery ---
        self.game_tick = QTimer(self)
        self.game_tick.timeout.connect(self._tick_threaded)
        self.game_tick.start(250)

        # Wyłączony automatyczny refresh — dane idą tylko po zakończeniu zlecenia
        self.points_timer = None

        self.refresh_labels(force=True)

    def _show_logged_user_on_brand(self):
        """Pokazuje aktualnie zalogowanego użytkownika w nagłówku"""
        if hasattr(self, "brand"):
            user = getattr(self, "logged_user", None)
            if user:
                try:
                    self.brand.set_user(user)
                except Exception:
                    pass
            else:
                try:
                    self.brand.set_user("Niezalogowany")
                except Exception:
                    pass

    def set_logged_user(self, login: str, name: str = ""):
        """Ustawia zalogowanego użytkownika w UI"""
        self.logged_user = name or login
        self._show_logged_user_on_brand()

    def change_lang(self):
        """Zmienia język interfejsu po zmianie w polu wyboru"""
        code = self.lang_box.currentData()
        self.lang = code if code in LANGS else "pl"
        self.tr = get_tr(self.lang)

        # Zaktualizuj teksty w UI
        try:
            self.tabs.setTabText(0, self.tr["tab_main"])
            self.tabs.setTabText(1, self.tr["tab_breaks"])
            self.tabs.setTabText(2, self.tr["tab_overlay"])
            self.tabs.setTabText(3, "Dyspozytornia")
            self.tabs.setTabText(4, "Ustawienia")
            self.ping_btn.setText("🚦 " + self.tr["ping"])
        except Exception as e:
            print("[UI] change_lang:", e)

    def test_connection(self):
        """Testuje połączenie z serwerem / n8n"""
        import threading

        def _ping():
            try:
                res = self.net.get_json("/ping", timeout=3)
                msg = res.get("status", "ok") if isinstance(res, dict) else "OK"
                print(f"[NET] Ping OK → {msg}")
                self.statusBar().showMessage(f"Połączenie OK ({msg})", 3000)
            except Exception as e:
                print(f"[NET] Ping error: {e}")
                self.statusBar().showMessage(f"Błąd połączenia: {e}", 3000)

        threading.Thread(target=_ping, daemon=True).start()

    def send_status_bg(self):
        """Wysyła bieżący status telemetryczny w tle"""
        try:
            data = {
                "speed": getattr(self, "speed_kmh", 0),
                "engine_on": getattr(self, "engine_on", False),
                "parking_brake": getattr(self, "parking_brake", False),
                "driving_seconds": getattr(self, "driving_seconds", 0),
                "working_seconds": getattr(self, "working_seconds", 0),
                "break_seconds": getattr(self, "break_seconds", 0),
            }

            # Spróbuj wysłać dane przez NetClient
            if hasattr(self, "net") and self.net:
                try:
                    self.net.post_json("/telemetry/update", data)
                    # Możesz dodać logowanie lokalne:
                    # print(f"[Telemetry] Sent: {data}")
                except Exception as e:
                    print(f"[Telemetry] send failed: {e}")

        except Exception as e:
            print(f"[Telemetry] Unexpected error in send_status_bg: {e}")

    def complete_job(self):
        """Zakończenie zlecenia – wysyła raport do n8n."""
        self.current_job_status = "completed"
        send_event_to_n8n(self, "job_complete", "Zakończono zlecenie", {
            "distance_km": getattr(self.telemetry_service.db, "get_total_distance", lambda: 0)(),
            "time_driven_sec": self.driving_seconds,
            "breaks_taken_sec": self.break_seconds,
        })
        self.statusBar().showMessage("Zlecenie zakończone – dane wysłane do n8n.", 4000)

    def _load_tab_on_demand(self, index: int):
        """Tworzy zakładki dopiero przy pierwszym otwarciu (lazy loading)"""
        if index in getattr(self, "_tabs_loaded", set()):
            return

        if index == 1:
            self.breaksTab = BreaksTab(self)
            self.tabs.addTab(self.breaksTab, self.tr["tab_breaks"])
        elif index == 2:
            self.overlayTab = OverlayTab(self.tr)
            self.tabs.addTab(self.overlayTab, self.tr["tab_overlay"])
        elif index == 3:
            self.dispatcherTab = DispatcherTab(n8n_client=self.net)
            self.tabs.addTab(self.dispatcherTab, "Dyspozytornia")
        elif index == 4:
            self.settingsTab = SettingsTab(self.tr)
            self.tabs.addTab(self.settingsTab, "Ustawienia")

        self._tabs_loaded.add(index)
        print(f"[UI] Załadowano zakładkę nr {index}")

    def _tick_threaded(self):
        import threading
        threading.Thread(target=self.tick_from_game, daemon=True).start()

    def _optimize_tab_switch(self, index):
        """Optymalizacja przełączania zakładek – tymczasowe wyłączenie redraw."""
        self.setUpdatesEnabled(False)
        try:
            self.tabs.setCurrentIndex(index)
        finally:
            self.setUpdatesEnabled(True)

    def complete_job(self):
        """Obsługa zakończenia zlecenia – wysyła raport do n8n i odświeża interfejs."""
        try:
            # przykładowe dane końcowe zlecenia
            payload = {
                "driver_id": getattr(self, "logged_user", "DRV001"),
                "job_status": "completed",
                "distance_km": getattr(self, "telemetry_service", None).db.get_total_distance() if hasattr(
                    self.telemetry_service, "db") else 0,
                "time_driven_sec": self.driving_seconds,
                "breaks_taken": self.break_seconds,
                "timestamp": "auto",
            }

            print("[DISPATCH] Wysyłam dane o zakończonym zleceniu do n8n...")
            if hasattr(self, "net") and self.net:
                try:
                    self.net.post_json("/job/complete", payload)
                    self.statusBar().showMessage("Zlecenie zakończone – dane wysłane do n8n.", 4000)
                except Exception as e:
                    print(f"[DISPATCH] błąd wysyłania: {e}")
                    self.statusBar().showMessage(f"Błąd wysyłania do n8n: {e}", 4000)
            else:
                print("[DISPATCH] Brak połączenia z n8n.")

        except Exception as e:
            print(f"[DISPATCH] Unexpected error in complete_job: {e}")

