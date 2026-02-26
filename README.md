# Arbeitseinteilung Web-App

Interne Webanwendung zur Mitarbeitereinsatzplanung, gebaut als Ersatz für die bisherige Excel-Lösung. Ermöglicht gleichzeitiges Bearbeiten durch mehrere Nutzer in Echtzeit.

## Features

- **Kalenderansicht**: Scrollbares Jahresview mit 3-Wochen-Standardansicht
- **Echtzeit-Bearbeitung**: Mehrere Nutzer können gleichzeitig arbeiten (Socket.IO)
- **Sondertage**: Farbkodierte Schnellauswahl (Urlaub, Krank, Schule, Innung, ...)
- **Mitarbeiterverwaltung**: Gruppen, Typen, Azubi-Blöcke, Leiharbeiter
- **Fahrzeugverwaltung**: Zuweisung, Status, Kraftstofftyp
- **Feiertage**: Automatisch für Hamburg, manuell erweiterbar
- **Änderungshistorie**: Wer hat wann was geändert
- **IP-basierte Nutzeridentifikation**: Keine Anmeldung nötig

## Voraussetzungen

- Docker & Docker Compose
- Raspberry Pi oder beliebiger Linux-Server
- Feste IP-Adressen der Arbeitsplätze (empfohlen)

## Installation

```bash
git clone <repo-url> arbeitseinteilung
cd arbeitseinteilung
docker-compose up -d --build
```

Die App ist danach erreichbar unter: `http://<server-ip>:6000`

## Aktualisieren

```bash
git pull
docker-compose up -d --build
```

## Datenbank

Die SQLite-Datenbank liegt unter `./data/arbeitseinteilung.db` und wird als Volume eingebunden – bleibt bei Updates erhalten.

## Stack

- **Backend**: Python / Flask + Flask-SocketIO
- **Datenbank**: SQLite
- **Server**: Gunicorn + Eventlet
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Echtzeit**: WebSockets via Socket.IO
- **Port**: 6000
