# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from ritt.integrations.events import send_event_to_n8n

class DispatcherTab(QWidget):
    """Widok kierowcy – bieżące zlecenie i interakcja z n8n."""
    def __init__(self, n8n_client=None, parent=None):
        super().__init__(parent)
        self.n8n_client = n8n_client
        self.parent_window = parent
        self.current_job = None
        self.new_job_data = None

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Sekcja bieżącego zlecenia ---
        self.title = QLabel("🚛  ZLECENIE AKTUALNE")
        self.title.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.label_job_id = QLabel("📦  Brak aktywnego zlecenia")
        self.label_route = QLabel("")
        self.label_distance = QLabel("")
        self.label_eta = QLabel("")

        # --- Przyciski ---
        self.btn_finish = QPushButton("✅  Zakończ zlecenie")
        self.btn_finish.clicked.connect(self.finish_job)
        self.btn_accept = QPushButton("✔️  Akceptuj nowe zlecenie")
        self.btn_accept.clicked.connect(self.accept_new_job)
        self.btn_accept.hide()

        # --- Układ ---
        for w in (self.title, self.label_job_id, self.label_route, self.label_distance, self.label_eta,
                  self.btn_finish, self.btn_accept):
            self.layout.addWidget(w)

    # -----------------------------------------------------------
    # API / logika
    # -----------------------------------------------------------

    def set_job_data(self, data: dict):
        """Ustawia dane aktualnego zlecenia."""
        self.current_job = data
        self.label_job_id.setText(f"📦  Numer zlecenia: {data.get('job_id', '---')}")
        self.label_route.setText(f"🛣️  Trasa: {data.get('route', '---')}")
        self.label_distance.setText(f"📏  Pozostały dystans: {data.get('remaining_km', '?')} km")
        self.label_eta.setText(f"🕒  ETA: {data.get('eta', '---')}")
        self.btn_finish.show()
        self.btn_accept.hide()

    def finish_job(self):
        """Kliknięcie 'Zakończ zlecenie' – wysyła do n8n."""
        if not self.current_job:
            QMessageBox.information(self, "Zlecenie", "Brak aktywnego zlecenia.")
            return

        send_event_to_n8n(self.parent_window, "job_complete",
                          f"Zakończono zlecenie {self.current_job.get('job_id', '---')}",
                          self.current_job)

        # aktualizacja UI
        self.label_job_id.setText("📦  Zlecenie zakończone, oczekiwanie na nowe…")
        self.label_route.setText("")
        self.label_distance.setText("")
        self.label_eta.setText("")
        self.btn_finish.hide()

        # symulacja – w realu n8n wyśle webhook /job/new
        self.request_new_job_from_n8n()

    def request_new_job_from_n8n(self):
        """Pobiera nowe zlecenie z n8n."""
        try:
            if self.n8n_client:
                data = self.n8n_client.get_json("/ritt/job/next")
                if isinstance(data, dict):
                    self.new_job_data = data
                    self.title.setText("🆕  NOWE ZLECENIE DOSTĘPNE")
                    self.label_job_id.setText(f"📦  Numer: {data.get('job_id', '?')}")
                    self.label_route.setText(f"🛣️  Trasa: {data.get('route', '?')}")
                    self.label_distance.setText(f"📏  Dystans: {data.get('distance_km', '?')} km")
                    self.label_eta.setText(f"⏱️  Czas: {data.get('expected_time_min', '?')} min")
                    self.btn_accept.show()
        except Exception as e:
            self.label_job_id.setText(f"❌ Błąd pobierania: {e}")

    def accept_new_job(self):
        """Kierowca akceptuje nowe zlecenie."""
        if not self.new_job_data:
            QMessageBox.information(self, "Zlecenie", "Brak nowego zlecenia do akceptacji.")
            return

        send_event_to_n8n(self.parent_window, "job_accept",
                          f"Zaakceptowano zlecenie {self.new_job_data.get('job_id', '---')}",
                          self.new_job_data)

        self.set_job_data(self.new_job_data)
        self.title.setText("🚛  ZLECENIE AKTUALNE")
        self.new_job_data = None
