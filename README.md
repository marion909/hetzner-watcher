# Hetzner CX43 Watcher

Dieses kleine Python-Skript prüft alle **30 Sekunden**, ob der Hetzner-Cloud-Servertyp **CX43** wieder verfügbar ist.

Sobald er in einer überwachten Location verfügbar ist, wird eine **E-Mail** verschickt.

Es nutzt die **offizielle Hetzner Cloud API** und prüft das Feld `server_type.locations[].available`.

## Dateien

- `watch_hetzner.py` – der Watcher
- `.env.example` – Beispiel-Konfiguration
- `start-watcher.cmd` – startet den Dauerlauf unter Windows
- `check-once.cmd` – macht genau einen Test-Check

## Voraussetzungen

- Windows mit `python` im Pfad
- Hetzner Cloud API Token
- SMTP-Zugang für den Mailversand

## Einrichtung

### 1) Ordner öffnen

Der Watcher liegt hier:

`Documents\hetzner-cx43-watcher`

### 2) Konfiguration anlegen

Kopiere `.env.example` nach `.env`.

In PowerShell:

```powershell
Copy-Item .env.example .env
```

Dann `.env` bearbeiten.

Wichtig sind mindestens:

- `HCLOUD_TOKEN`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_SECURITY`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_TO`

### 3) Optional: auf bestimmte Locations einschränken

Wenn du nur bestimmte Standorte willst:

```env
HETZNER_LOCATIONS=fsn1,nbg1,hel1
```

Wenn das Feld leer bleibt, prüft das Skript **alle unterstützten Locations** für `cx43`.

## Starten

### Einmal testen

```powershell
python .\watch_hetzner.py --once
```

oder per Doppelklick:

`check-once.cmd`

### Test-E-Mail senden

```powershell
python .\watch_hetzner.py --test-email
```

### Dauerlauf starten

```powershell
python .\watch_hetzner.py
```

oder per Doppelklick:

`start-watcher.cmd`

## Verhalten

- Polling standardmäßig alle **30 Sekunden**
- E-Mail nur **einmal pro Verfügbarkeitsphase**
- Wenn der Typ wieder ausverkauft ist, wird der Alarm zurückgesetzt
- Wenn er später erneut verfügbar wird, kommt wieder eine E-Mail

Die Statusdatei liegt standardmäßig in:

`state.json`

## Nützliche Optionen

### Nach Alarm stoppen

Wenn das Skript nach der ersten erfolgreichen Mail enden soll:

```env
STOP_AFTER_ALERT=true
```

### Anderen Servertyp prüfen

```env
HETZNER_SERVER_TYPE=cx43
```

Du kannst hier auch andere Typen eintragen.

## Hinweise zu SMTP

- Bei Gmail brauchst du in der Regel ein **App-Passwort**
- `SMTP_SECURITY` kann sein:
  - `starttls`
  - `ssl`
  - `none`

Typische Werte:

- STARTTLS: Port `587`
- SSL: Port `465`

## Beispiel

```env
HCLOUD_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HETZNER_SERVER_TYPE=cx43
HETZNER_LOCATIONS=fsn1,nbg1,hel1
CHECK_INTERVAL_SECONDS=30
STOP_AFTER_ALERT=false

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=dein.name@gmail.com
SMTP_PASSWORD=dein_app_passwort
EMAIL_FROM=dein.name@gmail.com
EMAIL_TO=dein.name@gmail.com
```

## Schnellstart

```powershell
cd $HOME\Documents\hetzner-cx43-watcher
Copy-Item .env.example .env
notepad .env
python .\watch_hetzner.py --test-email
python .\watch_hetzner.py
```
