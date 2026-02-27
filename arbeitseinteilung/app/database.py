import sqlite3
from flask import g, current_app
from .helpers import get_hamburg_holidays


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=10  # Warte bis zu 10s auf Write-Lock statt sofort zu crashen
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = sqlite3.connect(
            app.config['DATABASE_PATH'],
            timeout=10
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")

        db.executescript("""
            CREATE TABLE IF NOT EXISTS mitarbeiter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                personalnummer TEXT,
                gruppe TEXT NOT NULL DEFAULT 'KD',
                typ TEXT NOT NULL DEFAULT 'Monteur',
                fuehrerschein INTEGER DEFAULT 0,
                azubi_block TEXT,
                betreuer_id INTEGER,
                verleihfirma TEXT,
                einsatz_von DATE,
                einsatz_bis DATE,
                aktiv INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (betreuer_id) REFERENCES mitarbeiter(id)
            );

            CREATE TABLE IF NOT EXISTS fahrzeuge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kennzeichen TEXT NOT NULL,
                baujahr TEXT,
                kraftstoff TEXT DEFAULT 'D',
                status TEXT DEFAULT 'Aktiv',
                status_kommentar TEXT,
                mitarbeiter_id INTEGER,
                aktiv INTEGER DEFAULT 1,
                FOREIGN KEY (mitarbeiter_id) REFERENCES mitarbeiter(id)
            );

            CREATE TABLE IF NOT EXISTS einsaetze (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mitarbeiter_id INTEGER NOT NULL,
                datum DATE NOT NULL,
                inhalt TEXT,
                UNIQUE(mitarbeiter_id, datum),
                FOREIGN KEY (mitarbeiter_id) REFERENCES mitarbeiter(id)
            );

            CREATE TABLE IF NOT EXISTS feiertage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum DATE NOT NULL UNIQUE,
                bezeichnung TEXT NOT NULL,
                automatisch INTEGER DEFAULT 1,
                halbtag INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS ip_nutzer (
                ip_adresse TEXT PRIMARY KEY,
                mitarbeiter_id INTEGER,
                zuletzt_gesehen DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mitarbeiter_id) REFERENCES mitarbeiter(id)
            );

            CREATE TABLE IF NOT EXISTS aenderungshistorie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zeitstempel DATETIME DEFAULT CURRENT_TIMESTAMP,
                bearbeiter_name TEXT,
                bearbeiter_ip TEXT,
                mitarbeiter_id INTEGER,
                mitarbeiter_name TEXT,
                datum DATE,
                wert_vorher TEXT,
                wert_nachher TEXT
            );

            -- Migrations-Versionstabelle
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            );

            -- Indizes für Abfrage-Performance
            CREATE INDEX IF NOT EXISTS idx_einsaetze_datum
                ON einsaetze(datum);
            CREATE INDEX IF NOT EXISTS idx_historie_zeitstempel
                ON aenderungshistorie(zeitstempel DESC);
            CREATE INDEX IF NOT EXISTS idx_historie_mitarbeiter
                ON aenderungshistorie(mitarbeiter_id);
        """)

        # ─── Versionierte Migrationen ─────────────────────────────────────────
        row = db.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current_version = row[0] if row[0] is not None else 0

        if current_version < 1:
            # Migration 1: halbtag-Spalte in feiertage einführen
            try:
                db.execute("ALTER TABLE feiertage ADD COLUMN halbtag INTEGER DEFAULT 0")
                db.execute("UPDATE feiertage SET halbtag=1 WHERE bezeichnung IN ('Heiligabend', 'Silvester')")
            except sqlite3.OperationalError:
                pass  # Spalte existiert bereits (frische DB hat sie schon)
            db.execute("INSERT OR IGNORE INTO schema_version VALUES (1)")

        # Seed Feiertage if empty
        count = db.execute("SELECT COUNT(*) FROM feiertage").fetchone()[0]
        if count == 0:
            from datetime import date
            year = date.today().year
            for y in [year, year + 1]:
                for datum, name in get_hamburg_holidays(y):
                    halbtag = 1 if name in ['Heiligabend', 'Silvester'] else 0
                    try:
                        db.execute(
                            "INSERT OR IGNORE INTO feiertage (datum, bezeichnung, automatisch, halbtag) VALUES (?, ?, 1, ?)",
                            (datum.isoformat(), name, halbtag)
                        )
                    except Exception:
                        pass

        db.commit()
        db.close()
