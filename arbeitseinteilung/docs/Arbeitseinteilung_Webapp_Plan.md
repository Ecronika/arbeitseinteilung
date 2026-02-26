# Projektplan: Arbeitseinteilung Web-App

## Ausgangslage

Die bisherige Arbeitseinteilung wird als Excel-Datei auf einem Netzwerklaufwerk gepflegt. Da das Unternehmen gewachsen ist, führt die Einschränkung auf einen gleichzeitigen Bearbeiter zunehmend zu Problemen. Ziel ist eine Webanwendung, die dieselbe Übersichtlichkeit bietet, aber gleichzeitiges Bearbeiten durch mehrere Nutzer ermöglicht.

Die bestehende Infrastruktur umfasst einen Raspberry Pi mit Home Assistant, der bereits eine Flask/SQLite/Gunicorn-Anwendung (Werkzeugverwaltung) als Docker-Container betreibt. Die neue Anwendung soll parallel dazu auf **Port 8090** laufen.

---

## Technischer Stack

| Schicht | Technologie |
|---|---|
| Backend | Python / Flask + Flask-SocketIO |
| Datenbank | SQLite |
| Server | Gunicorn + Eventlet |
| Frontend | Vanilla HTML / CSS / JavaScript + Socket.IO |
| Echtzeit-Sync | WebSockets via Socket.IO |
| Deployment | Docker Container, Port 8090 |
| Datenmigration | Einmaliger Import aus bestehender Excel-Datei |

---

## Nutzeridentifikation (ohne Login)

Da keine Benutzeranmeldung vorgesehen ist (offenes Intranet), erfolgt die Identifikation über die **IP-Adresse des Arbeitsplatzes**:

- Beim ersten Aufruf erscheint ein Popup zur Namensauswahl (Auswahl aus Mitarbeiterliste)
- Die Zuordnung IP → Mitarbeiter wird in der Datenbank gespeichert
- Bei jedem weiteren Aufruf von derselben IP wird der Mitarbeiter automatisch vorausgewählt – das Popup erscheint mit vorausgefülltem Namen zur schnellen Bestätigung
- Abweichende Auswahl möglich (z.B. Vertretung an fremdem Rechner), mit Option „Für diesen PC speichern"
- Voraussetzung: Feste IP-Adressen je Arbeitsplatz (statisch oder per DHCP-Reservierung)

**Datenbank-Tabelle `ip_nutzer`:**

| Feld | Typ | Beschreibung |
|---|---|---|
| ip_adresse | TEXT | IP des Arbeitsplatzes |
| mitarbeiter_id | INTEGER | Zugeordneter Mitarbeiter |
| zuletzt_gesehen | DATETIME | Letzter Zugriff von dieser IP |

---

## Ansicht & Navigation

- **Standard-Ansicht:** 3-Wochen-Fenster (letzte, aktuelle und kommende Woche gleichzeitig sichtbar)
- **Scrollbar:** Das gesamte Jahr ist horizontal scrollbar (vertraute Excel-Gewohnheit)
- **Datumsauswahl:** Kalender-Picker zum Springen an beliebiges Datum
- **„Heute"-Button:** Springt sofort zur aktuellen Woche und hebt sie hervor
- **Wochenenden:** Schmaler dargestellt und ausgegraut (nicht ausgeblendet, da gelegentlich Samstagseinsätze vorkommen)
- **Feiertage:** Automatisch farblich markiert mit Tooltip (Name des Feiertags)

---

## Kalendermatrix (Hauptansicht)

### Zeilenstruktur

- Mitarbeiter gruppiert nach Abteilung: **KD / ST / KDF / MT / P1 / P2 / Büro**
- Gruppenheader als farbige Trennzeile
- Azubis: Schulblock (A/B/C) als Badge + Betreuer-Zuordnung sichtbar
- Leiharbeiter: Verleihfirma als Subtext unter dem Namen

### Zellbearbeitung

Klick auf eine Zelle öffnet ein kleines Popup mit:

1. **Freitext-Eingabe** – Baustelle oder Einsatzort
2. **Sondertag-Auswahl** – farbige Schaltflächen für schnelle Auswahl
3. **Löschen** – Zelle leeren

- Speichern erfolgt automatisch beim Schließen des Popups
- Während der Bearbeitung: Zelle erscheint für alle anderen Nutzer als gesperrt (Overlay mit Name des Bearbeiters)
- Änderung wird nach dem Speichern sofort bei allen verbundenen Nutzern angezeigt (WebSocket)

---

## Sondertage & Farbschema

| Bezeichnung | Kürzel | Farbe |
|---|---|---|
| Urlaub | Urlaub | Gelb |
| Krank | Krank | Rot |
| Berufsschule | Schule | Blau |
| Innung | Innung | Orange |
| Überstunden | Überstd. | Grün |
| Kurzarbeit | KUG | Grau |
| Prüfungsvorbereitung | P | Hellblau |
| Mutterschutz | Mutterschutz | Rosa |
| Quarantäne | Q | Lila |
| Feiertag | (automatisch) | Dunkelgrau |

> Die genauen Hex-Farbwerte werden noch gegen die originale Excel-Datei abgeglichen.

---

## Mitarbeiterverwaltung

### Stammdaten je Mitarbeiter

| Feld | Beschreibung |
|---|---|
| Name | Vollständiger Name |
| Personalnummer | Interne Nummer |
| Gruppe | KD / ST / KDF / MT / P1 / P2 / Büro |
| Typ | Monteur / Azubi / Leiharbeiter / Praktikant |
| Führerschein | Ja / Nein |
| Azubi-Block | A / B / C (nur bei Azubis) |
| Betreuer | Zugeordneter Stammmonteur (nur bei Azubis) |
| Verleihfirma | Name der Zeitarbeitsfirma (nur bei Leiharbeitern) |
| Einsatzzeitraum | Von/Bis (nur bei Leiharbeitern) |
| Aktiv | Ja / Nein (deaktivierte Mitarbeiter bleiben in der Historik) |

### Aktionen

- Gruppe wechseln (Dropdown oder Drag & Drop)
- Mitarbeiter deaktivieren (kein Löschen – Historik bleibt erhalten)
- Leiharbeiter schnell anlegen über vereinfachtes Formular
- Leiharbeiter werden nach Ablauf des Einsatzzeitraums automatisch inaktiv gesetzt

---

## Fahrzeugverwaltung

### Stammdaten je Fahrzeug

| Feld | Beschreibung |
|---|---|
| Kennzeichen | z.B. HH CB 1332 |
| Baujahr | Zweistellig, z.B. 24 = 2024 |
| Kraftstoff | B = Benzin / D = Diesel / E = Elektro / Hybrid |
| Status | Aktiv / Geparkt / Werkstatt / Defekt |
| Statuskommentar | Freitext, z.B. „TÜV fällig 15.03." |
| Zugeordneter Mitarbeiter | Aktueller Fahrer |

### Aktionen

- Fahrzeug einem anderen Mitarbeiter zuweisen
- Status ändern mit optionalem Kommentar
- Fahrzeuge ohne Zuordnung als „verfügbar" anzeigen

---

## Feiertage

- Automatisch vorbelegt mit allen Hamburger Feiertagen des aktuellen und nächsten Jahres
- Manuell ergänzbar (z.B. Betriebsferien, Brückentage)
- Manuell löschbar, falls ein Feiertag nicht zutrifft
- Separate Verwaltungsseite

---

## Änderungshistorie

Jede Zelländerung wird vollständig protokolliert:

| Feld | Beschreibung |
|---|---|
| Zeitstempel | Datum und Uhrzeit der Änderung |
| Bearbeiter | Name des Nutzers (aus IP-Zuordnung) |
| Mitarbeiter-Zeile | Betroffener Mitarbeiter |
| Datum | Betroffener Kalendertag |
| Wert vorher | Alter Zelleninhalt |
| Wert nachher | Neuer Zelleninhalt |

- Historien-Ansicht filterbar nach Mitarbeiter, Datum oder Bearbeiter
- Kein automatisches Löschen – Historik bleibt dauerhaft erhalten

---

## Datenbankstruktur (Übersicht)

| Tabelle | Beschreibung |
|---|---|
| `mitarbeiter` | Stammdaten aller Mitarbeiter |
| `fahrzeuge` | Stammdaten aller Fahrzeuge |
| `einsaetze` | Tageseinträge (Mitarbeiter + Datum + Inhalt) |
| `sondertage` | Definition der Sondertag-Typen mit Farben |
| `feiertage` | Hamburger Feiertage + manuelle Einträge |
| `ip_nutzer` | IP-Adresse → Mitarbeiter-Zuordnung |
| `aenderungshistorie` | Vollständiges Änderungsprotokoll |

---

## Deployment (Docker)

- Eigenständiger Docker-Container, unabhängig von der bestehenden Werkzeugverwaltung
- Port: **8090**
- Registrierung als Home Assistant Addon parallel zur bestehenden Anwendung
- Datenbankdatei (`arbeitseinteilung.db`) als Volume eingebunden für persistente Datenspeicherung

---

## Noch offene Punkte

- [ ] Exakte Hex-Farbwerte der Sondertage aus Excel-Datei übernehmen
- [ ] Feste IP-Adressen der Arbeitsplätze sicherstellen (statisch oder DHCP-Reservierung)
- [ ] Entscheidung: Soll die historische Excel-Daten (2012–2025) migriert werden, oder startet die App mit einem leeren Datenbestand?
- [ ] Festlegung der Gruppen-Trennfarben in der Kalenderansicht

---

*Erstellt: Februar 2026 – Version 1.0*
