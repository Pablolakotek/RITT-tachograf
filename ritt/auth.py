# -*- coding: utf-8 -*-
import os
import json
from typing import Tuple, Optional

# Opcjonalny, bezpieczny magazyn haseł (Windows Credential Manager / macOS Keychain / GNOME Keyring)
try:
    import keyring  # pip install keyring
    KEYRING_AVAILABLE = True
except Exception:
    keyring = None
    KEYRING_AVAILABLE = False

# Ten sam endpoint co wcześniej (WP)
API_LOGIN_URL = "https://ritt.org.uk/wp-json/tachograph/v1/login"

import requests

CREDS_FILE = os.path.join(os.path.expanduser("~"), ".tachograf_creds.json")
KEYRING_SERVICE = "tachograf_ritt"


def _read_json() -> dict:
    try:
        if os.path.exists(CREDS_FILE):
            with open(CREDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _write_json(data: dict) -> None:
    try:
        with open(CREDS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def authenticate_driver(username: str, password: str, api_url: str = API_LOGIN_URL, timeout: int = 8) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Zwraca: (ok, driver_id, error)
    """
    try:
        resp = requests.post(
            api_url,
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success" and "driver_id" in data:
                return True, str(data["driver_id"]), None
            return False, None, data.get("message") or "Błędne dane logowania."
        return False, None, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.RequestException as e:
        return False, None, f"Błąd sieci: {e}"


def load_saved_credentials() -> Tuple[str, str, bool, bool]:
    """
    Wczytuje zapamiętane dane.
    Zwraca: (username, password, remember_username, remember_password)
    """
    d = _read_json()
    username = d.get("username", "")
    remember_username = bool(d.get("remember_username", bool(username)))
    remember_password = bool(d.get("remember_password", False))

    password = ""
    # Preferuj keyring
    if remember_password and username:
        if KEYRING_AVAILABLE:
            try:
                got = keyring.get_password(KEYRING_SERVICE, username)
                if got:
                    password = got
            except Exception:
                pass
        # Fallback: plik JSON (kompatybilność wsteczna)
        if not password:
            password = d.get("password", "")

    return username, password, remember_username, remember_password


def save_credentials(username: str, remember_username: bool, password: str, remember_password: bool, prev_username: str = "") -> None:
    """
    Zapisuje ustawienia „zapamiętaj login/hasło”.
    - login zapisujemy w JSON jeśli remember_username == True
    - hasło zapisujemy w keyring (jeśli dostępny) lub w JSON (fallback) tylko gdy remember_password == True
    - czyścimy poprzednie hasło, jeśli user zmienił login lub odznaczył „zapamiętaj hasło”
    """
    d = _read_json()

    # login
    d["remember_username"] = bool(remember_username)
    d["remember_password"] = bool(remember_password)
    d["username"] = username if remember_username else ""

    # jeśli zmienił się login, usuń stare hasło z keyring
    if prev_username and prev_username != username:
        clear_password(prev_username)

    # hasło
    if remember_password and username:
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYRING_SERVICE, username, password or "")
            except Exception:
                # fallback do pliku jeśli keyring zawiódł
                d["password"] = password or ""
        else:
            d["password"] = password or ""
    else:
        # nie zapamiętuj hasła
        clear_password(username)
        # usuń z JSON
        if "password" in d:
            d.pop("password", None)

    _write_json(d)


def clear_password(username: str) -> None:
    """Usuwa zapisane hasło danego użytkownika (keyring + JSON)."""
    if username and KEYRING_AVAILABLE:
        try:
            keyring.delete_password(KEYRING_SERVICE, username)
        except Exception:
            pass
    d = _read_json()
    if "password" in d:
        d.pop("password", None)
        _write_json(d)
