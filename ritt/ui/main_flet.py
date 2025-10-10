# -*- coding: utf-8 -*-
import flet as ft
import uuid
from ritt.n8n_config import load_from_ini
from ritt.n8n import N8nClient, N8nEndpoints
from ritt.save_ops import backup_file, apply_patch


def init_n8n_client():
    """Inicjalizuje klienta n8n (bez zmian względem wersji PySide6)."""
    cfg = load_from_ini("ritt.ini")

    endpoints = N8nEndpoints(
        base_url=cfg.n8n.base_url,
        ingest_path=cfg.n8n.ingest_path,
        commands_path=cfg.n8n.commands_path,
        ack_path=cfg.n8n.ack_path,
    )

    client = N8nClient(
        endpoints=endpoints,
        hmac_secret=cfg.n8n.hmac_secret,
        send_interval_ms=cfg.send_interval_ms,
        batch_size=cfg.batch_size,
        retry_max=cfg.retry_max,
        dry_run=cfg.dry_run,
        timezone=cfg.timezone,
    )

    def handle_command(cmd: dict):
        t = cmd.get("cmd_type", "")
        args = cmd.get("args", {}) or {}

        if t == "message":
            text = args.get("text", "")
            print(f"[n8n] Message from dispatcher: {text}")
            return "ok", text, {}

        if t == "save_patch":
            save_file = args.get("save_file")
            if not save_file:
                save_file = cfg.save.dir.rstrip("\\/") + "\\game.sii"

            backup = backup_file(save_file, cfg.save.backup_dir)
            ok, msg, det = apply_patch(save_file, args.get("patch", {}))
            det.update({"backup": backup})
            return ("ok" if ok else "failed"), msg, det

        return "ok", f"Unhandled cmd_type={t}", {}

    client.set_command_handler(handle_command)
    session_id = f"SESSION-{uuid.uuid4()}"
    client.start(session_id=session_id)
    print(f"[n8n] Started session {session_id}")
    return client


def main(page: ft.Page):
    """Nowy interfejs Flet zamiast PySide6 GUI"""
    page.title = "RITT Tachograph"
    page.theme_mode = "dark"
    page.bgcolor = "#121212"

    # Inicjalizacja n8n
    n8n_client = init_n8n_client()

    # Sekcje
    dispatcher_tab = ft.Column([
        ft.Text("📡 Dyspozytornia", size=28, weight="bold"),
        ft.Text("Podgląd statusów kierowców", size=16),
        ft.ElevatedButton("Wyślij testowy event", icon=ft.icons.SEND,
                          on_click=lambda e: n8n_client.enqueue_event(
                              event_type="test_event",
                              driver_id="DRV001",
                              vehicle_id="TRK_01",
                              status="ok"))
    ])

    tacho_tab = ft.Column([
        ft.Text("⏱ Tachograf", size=28, weight="bold"),
        ft.Row([
            ft.ElevatedButton("Start jazdy", icon=ft.icons.PLAY_ARROW,
                              on_click=lambda e: n8n_client.enqueue_event(
                                  event_type="start_drive", driver_id="DRV001")),
            ft.ElevatedButton("Stop jazdy", icon=ft.icons.STOP,
                              on_click=lambda e: n8n_client.enqueue_event(
                                  event_type="stop_drive", driver_id="DRV001"))
        ])
    ])

    settings_tab = ft.Column([
        ft.Text("⚙️ Ustawienia", size=28, weight="bold"),
        ft.TextField(label="Webhook URL",
                     hint_text="https://n8n.ox-ram.uk/webhook/ritt/ingest"),
        ft.Switch(label="Auto-raporty", value=True),
        ft.ElevatedButton("Zapisz", icon=ft.icons.SAVE)
    ])

    # Nawigacja boczna
    nav = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Dyspozytornia"),
            ft.NavigationRailDestination(icon=ft.icons.SPEED, label="Tachograf"),
            ft.NavigationRailDestination(icon=ft.icons.SETTINGS, label="Ustawienia"),
        ],
        bgcolor="#1E1E1E"
    )

    content = ft.Container(content=dispatcher_tab, expand=True, padding=20)

    def on_nav_change(e):
        idx = e.control.selected_index
        if idx == 0:
            content.content = dispatcher_tab
        elif idx == 1:
            content.content = tacho_tab
        else:
            content.content = settings_tab
        page.update()

    nav.on_change = on_nav_change

    # Główny layout
    page.add(ft.Row([nav, ft.VerticalDivider(width=1), content], expand=True))
