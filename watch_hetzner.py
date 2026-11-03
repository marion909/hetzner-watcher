#!/usr/bin/env python3
"""Überwacht die Verfügbarkeit eines Hetzner-Cloud-Servertyps (Standard: CX43)
und schickt eine E-Mail, sobald er in einer überwachten Location verfügbar ist."""

import argparse
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
API_URL = "https://api.hetzner.cloud/v1/server_types"


def ssl_context():
    # python.org-Builds auf macOS bringen keine CA-Zertifikate mit -> System-Bundle nutzen
    system_bundle = "/etc/ssl/cert.pem"
    if os.path.exists(system_bundle):
        return ssl.create_default_context(cafile=system_bundle)
    return ssl.create_default_context()


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def env(name, default=""):
    return os.environ.get(name, default).strip()


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def fetch_locations(token, server_type, timeout):
    """Liefert {location_name: available} für den Servertyp."""
    url = f"{API_URL}?{urllib.parse.urlencode({'name': server_type})}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
        data = json.load(resp)
    types = data.get("server_types", [])
    if not types:
        raise RuntimeError(f"Servertyp '{server_type}' nicht gefunden")
    result = {}
    for loc in types[0].get("locations", []):
        result[loc["name"]] = bool(loc.get("available", False))
    return result


def send_mail(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = env("EMAIL_FROM")
    msg["To"] = env("EMAIL_TO")
    msg.set_content(body)

    host = env("SMTP_HOST")
    port = int(env("SMTP_PORT", "587"))
    security = env("SMTP_SECURITY", "starttls").lower()
    timeout = int(env("SMTP_TIMEOUT_SECONDS", "20"))
    ctx = ssl_context()

    if security == "ssl":
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
    with server:
        if security == "starttls":
            server.starttls(context=ctx)
        if env("SMTP_USERNAME"):
            server.login(env("SMTP_USERNAME"), env("SMTP_PASSWORD"))
        server.send_message(msg)


def load_state(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def check(state, state_path, args_once):
    token = env("HCLOUD_TOKEN")
    server_type = env("HETZNER_SERVER_TYPE", "cx43")
    timeout = int(env("REQUEST_TIMEOUT_SECONDS", "15"))
    wanted = [x.strip() for x in env("HETZNER_LOCATIONS").split(",") if x.strip()]

    locations = fetch_locations(token, server_type, timeout)
    if wanted:
        locations = {k: v for k, v in locations.items() if k in wanted}
    available = sorted(k for k, v in locations.items() if v)
    log(f"{server_type}: verfügbar in {', '.join(available) or '-'} "
        f"(geprüft: {', '.join(sorted(locations)) or '-'})")

    if not available:
        if state.get("alerted"):
            log("Wieder ausverkauft – Alarm zurückgesetzt.")
        state["alerted"] = False
        save_state(state_path, state)
        return False

    if state.get("alerted"):
        return False

    send_mail(
        f"Hetzner {server_type.upper()} ist verfügbar!",
        f"{server_type.upper()} ist jetzt verfügbar in: {', '.join(available)}\n\n"
        "https://console.hetzner.cloud/",
    )
    log("E-Mail gesendet.")
    state["alerted"] = True
    save_state(state_path, state)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="genau ein Check")
    parser.add_argument("--test-email", action="store_true", help="Test-Mail senden")
    args = parser.parse_args()

    load_env(BASE_DIR / ".env")

    if args.test_email:
        send_mail("Hetzner Watcher Test", "Die E-Mail-Konfiguration funktioniert.")
        log("Test-E-Mail gesendet.")
        return 0

    if not env("HCLOUD_TOKEN"):
        log("HCLOUD_TOKEN fehlt in .env")
        return 1

    state_path = Path(env("STATE_FILE", "state.json"))
    if not state_path.is_absolute():
        state_path = BASE_DIR / state_path
    state = load_state(state_path)
    interval = int(env("CHECK_INTERVAL_SECONDS", "30"))
    stop_after = env("STOP_AFTER_ALERT", "false").lower() == "true"

    while True:
        try:
            alerted = check(state, state_path, args.once)
            if alerted and stop_after:
                return 0
        except (urllib.error.URLError, smtplib.SMTPException, OSError, RuntimeError) as exc:
            log(f"Fehler: {exc}")
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
