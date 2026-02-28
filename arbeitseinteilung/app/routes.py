"""HTTP-Routen und API-Endpunkte für Arbeitseinteilung."""

import csv
import io
import sqlite3
from datetime import date, datetime

from flask import Blueprint, Response, jsonify, render_template, request

from .database import get_db
from .helpers import (
    GRUPPEN_FARBEN,
    GRUPPEN_REIHENFOLGE,
    SONDERTAG_FARBEN,
    get_hamburg_holidays,
)

bp = Blueprint('main', __name__)

# ─── Validierungskonstanten ──────────────────────────────────────────────────

MAX_INHALT_LEN = 500
MAX_BEZEICHNUNG_LEN = 200
MAX_NAME_LEN = 100
MAX_KENNZEICHEN_LEN = 20


def get_client_ip() -> str:
    """Gib die IP-Adresse des anfragenden Clients zurück.

    Returns:
        IP-Adresse als String (z. B. '192.168.1.42').
    """
    return request.remote_addr


# ─── SEITEN ──────────────────────────────────────────────────────────────────

@bp.route('/')
def index():
    """Rendere die Kalender-Hauptseite."""
    return render_template(
        'index.html',
        sondertag_farben=SONDERTAG_FARBEN,
        gruppen_farben=GRUPPEN_FARBEN,
        gruppen_reihenfolge=GRUPPEN_REIHENFOLGE,
    )


@bp.route('/mitarbeiter-verwaltung')
def mitarbeiter_seite():
    """Rendere die Mitarbeiterverwaltungsseite."""
    return render_template('mitarbeiter.html', gruppen=GRUPPEN_REIHENFOLGE, gruppen_farben=GRUPPEN_FARBEN)


@bp.route('/fahrzeuge-verwaltung')
def fahrzeuge_seite():
    """Rendere die Fahrzeugverwaltungsseite."""
    return render_template('fahrzeuge.html')


@bp.route('/feiertage-verwaltung')
def feiertage_seite():
    """Rendere die Feiertagsverwaltungsseite."""
    return render_template('feiertage.html')


@bp.route('/historie')
def historie_seite():
    """Rendere die Änderungshistorie-Seite."""
    return render_template('historie.html')


# ─── IP / NUTZER ──────────────────────────────────────────────────────────────

@bp.route('/api/mein-nutzer')
def mein_nutzer():
    """Gib den Mitarbeiter zurück, der dieser IP-Adresse zugeordnet ist.

    Returns:
        JSON mit ``mitarbeiter_id``, ``name`` und ``ip``.
    """
    ip = get_client_ip()
    db = get_db()
    row = db.execute(
        """SELECT ip_nutzer.mitarbeiter_id, mitarbeiter.name
           FROM ip_nutzer
           LEFT JOIN mitarbeiter ON mitarbeiter.id = ip_nutzer.mitarbeiter_id
           WHERE ip_nutzer.ip_adresse = ?""",
        (ip,)
    ).fetchone()
    if row and row['mitarbeiter_id']:
        db.execute("UPDATE ip_nutzer SET zuletzt_gesehen=CURRENT_TIMESTAMP WHERE ip_adresse=?", (ip,))
        db.commit()
        return jsonify({"mitarbeiter_id": row['mitarbeiter_id'], "name": row['name'], "ip": ip})
    return jsonify({"mitarbeiter_id": None, "name": None, "ip": ip})


@bp.route('/api/ip-nutzer', methods=['POST'])
def set_ip_nutzer():
    """Ordne die aktuelle IP-Adresse einem Mitarbeiter zu.

    Returns:
        JSON mit ``ok: true`` bei Erfolg oder Fehlermeldung.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if 'mitarbeiter_id' not in data:
        return jsonify({"error": "mitarbeiter_id required"}), 422
    ip = get_client_ip()
    db = get_db()
    db.execute(
        """INSERT INTO ip_nutzer (ip_adresse, mitarbeiter_id, zuletzt_gesehen)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(ip_adresse) DO UPDATE SET
               mitarbeiter_id=excluded.mitarbeiter_id,
               zuletzt_gesehen=CURRENT_TIMESTAMP""",
        (ip, data['mitarbeiter_id'])
    )
    db.commit()
    return jsonify({"ok": True})


# ─── MITARBEITER ──────────────────────────────────────────────────────────────

@bp.route('/api/mitarbeiter')
def get_mitarbeiter():
    """Gib alle aktiven Mitarbeiter gruppiert und als Flachliste zurück.

    Returns:
        JSON mit ``gruppen`` (nach Gruppe) und ``alle`` (Flachliste).
    """
    db = get_db()
    rows = db.execute("""
        SELECT m.*, f.kennzeichen, f.baujahr, f.kraftstoff,
               b.name as betreuer_name
        FROM mitarbeiter m
        LEFT JOIN fahrzeuge f ON f.mitarbeiter_id = m.id AND f.aktiv = 1
            AND f.id = (SELECT MIN(id) FROM fahrzeuge WHERE mitarbeiter_id = m.id AND aktiv = 1)
        LEFT JOIN mitarbeiter b ON b.id = m.betreuer_id
        WHERE m.aktiv = 1 AND (m.einsatz_bis IS NULL OR m.einsatz_bis >= date('now', 'localtime'))
        ORDER BY m.gruppe, m.sort_order, m.name
    """).fetchall()

    gruppen: dict = {}
    for gruppe in GRUPPEN_REIHENFOLGE:
        gruppen[gruppe] = []

    for r in rows:
        d = dict(r)
        gruppe = d.get('gruppe', 'KD')
        if gruppe not in gruppen:
            gruppen[gruppe] = []
        gruppen[gruppe].append(d)

    return jsonify({"gruppen": gruppen, "alle": [dict(r) for r in rows]})


@bp.route('/api/mitarbeiter', methods=['POST'])
def create_mitarbeiter():
    """Lege einen neuen Mitarbeiter an.

    Returns:
        JSON mit ``id`` des neu angelegten Mitarbeiters und ``ok: true``.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({"error": "name required"}), 422
    if len(name) > MAX_NAME_LEN:
        return jsonify({"error": f"name darf maximal {MAX_NAME_LEN} Zeichen lang sein"}), 422
    db = get_db()
    cur = db.execute("""
        INSERT INTO mitarbeiter
            (name, personalnummer, gruppe, typ, fuehrerschein, azubi_block,
             betreuer_id, verleihfirma, einsatz_von, einsatz_bis, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, data.get('personalnummer'), data.get('gruppe', 'KD'),
        data.get('typ', 'Monteur'), 1 if data.get('fuehrerschein') else 0,
        data.get('azubi_block'), data.get('betreuer_id'),
        data.get('verleihfirma'), data.get('einsatz_von'), data.get('einsatz_bis'),
        data.get('sort_order', 0)
    ))
    db.commit()
    return jsonify({"id": cur.lastrowid, "ok": True})


@bp.route('/api/mitarbeiter/<int:mid>', methods=['PUT'])
def update_mitarbeiter(mid: int):
    """Aktualisiere einen bestehenden Mitarbeiterdatensatz.

    Args:
        mid: Datenbank-ID des zu aktualisierenden Mitarbeiters.

    Returns:
        JSON mit ``ok: true`` bei Erfolg.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({"error": "name required"}), 422
    if len(name) > MAX_NAME_LEN:
        return jsonify({"error": f"name darf maximal {MAX_NAME_LEN} Zeichen lang sein"}), 422
    db = get_db()
    db.execute("""
        UPDATE mitarbeiter SET
            name=?, personalnummer=?, gruppe=?, typ=?, fuehrerschein=?,
            azubi_block=?, betreuer_id=?, verleihfirma=?,
            einsatz_von=?, einsatz_bis=?, sort_order=?, aktiv=?
        WHERE id=?
    """, (
        name, data.get('personalnummer'), data.get('gruppe', 'KD'),
        data.get('typ', 'Monteur'), 1 if data.get('fuehrerschein') else 0,
        data.get('azubi_block'), data.get('betreuer_id'),
        data.get('verleihfirma'), data.get('einsatz_von'), data.get('einsatz_bis'),
        data.get('sort_order', 0), 1 if data.get('aktiv', True) else 0,
        mid
    ))
    db.commit()
    return jsonify({"ok": True})


@bp.route('/api/mitarbeiter/reorder', methods=['PUT'])
def reorder_mitarbeiter():
    """Aktualisiere die Sortierreihenfolge mehrerer Mitarbeiter.

    Returns:
        JSON mit ``ok: true`` bei Erfolg oder Fehlermeldung.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    orders = data.get('orders', [])
    try:
        db = get_db()
        for item in orders:
            db.execute(
                "UPDATE mitarbeiter SET sort_order = ? WHERE id = ?",
                (item.get('sort_order'), item.get('id'))
            )
        db.commit()
        return jsonify({"ok": True})
    except sqlite3.Error as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route('/api/mitarbeiter/<int:mid>', methods=['DELETE'])
def deactivate_mitarbeiter(mid: int):
    """Deaktiviere einen Mitarbeiter (Soft-Delete).

    Args:
        mid: Datenbank-ID des zu deaktivierenden Mitarbeiters.

    Returns:
        JSON mit ``ok: true``.
    """
    db = get_db()
    db.execute("UPDATE mitarbeiter SET aktiv=0 WHERE id=?", (mid,))
    db.commit()
    return jsonify({"ok": True})


# ─── FAHRZEUGE ────────────────────────────────────────────────────────────────

@bp.route('/api/fahrzeuge')
def get_fahrzeuge():
    """Gib alle aktiven Fahrzeuge mit zugeordnetem Mitarbeiter zurück.

    Returns:
        JSON-Array mit allen aktiven Fahrzeugen.
    """
    db = get_db()
    rows = db.execute("""
        SELECT f.*, m.name as mitarbeiter_name
        FROM fahrzeuge f
        LEFT JOIN mitarbeiter m ON m.id = f.mitarbeiter_id
        WHERE f.aktiv = 1
        ORDER BY f.kennzeichen
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.route('/api/fahrzeuge', methods=['POST'])
def create_fahrzeug():
    """Lege ein neues Fahrzeug an.

    Returns:
        JSON mit ``id`` des neu angelegten Fahrzeugs und ``ok: true``.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    kennzeichen = str(data.get('kennzeichen', '')).strip()
    if not kennzeichen:
        return jsonify({"error": "kennzeichen required"}), 422
    if len(kennzeichen) > MAX_KENNZEICHEN_LEN:
        return jsonify({"error": f"kennzeichen darf maximal {MAX_KENNZEICHEN_LEN} Zeichen lang sein"}), 422
    db = get_db()
    cur = db.execute("""
        INSERT INTO fahrzeuge (kennzeichen, baujahr, kraftstoff, status, status_kommentar, mitarbeiter_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        kennzeichen, data.get('baujahr'), data.get('kraftstoff', 'D'),
        data.get('status', 'Aktiv'), data.get('status_kommentar'), data.get('mitarbeiter_id')
    ))
    db.commit()
    return jsonify({"id": cur.lastrowid, "ok": True})


@bp.route('/api/fahrzeuge/<int:fid>', methods=['PUT'])
def update_fahrzeug(fid: int):
    """Aktualisiere ein bestehendes Fahrzeug.

    Args:
        fid: Datenbank-ID des zu aktualisierenden Fahrzeugs.

    Returns:
        JSON mit ``ok: true`` bei Erfolg.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    kennzeichen = str(data.get('kennzeichen', '')).strip()
    if not kennzeichen:
        return jsonify({"error": "kennzeichen required"}), 422
    if len(kennzeichen) > MAX_KENNZEICHEN_LEN:
        return jsonify({"error": f"kennzeichen darf maximal {MAX_KENNZEICHEN_LEN} Zeichen lang sein"}), 422
    db = get_db()
    db.execute("""
        UPDATE fahrzeuge SET
            kennzeichen=?, baujahr=?, kraftstoff=?, status=?,
            status_kommentar=?, mitarbeiter_id=?, aktiv=?
        WHERE id=?
    """, (
        kennzeichen, data.get('baujahr'), data.get('kraftstoff', 'D'),
        data.get('status', 'Aktiv'), data.get('status_kommentar'),
        data.get('mitarbeiter_id'), 1 if data.get('aktiv', True) else 0,
        fid
    ))
    db.commit()
    return jsonify({"ok": True})


# ─── EINSÄTZE ─────────────────────────────────────────────────────────────────

@bp.route('/api/einsaetze')
def get_einsaetze():
    """Gib alle Einsätze im angefragten Datumsbereich zurück.

    Query-Parameter:
        von: Startdatum (YYYY-MM-DD).
        bis: Enddatum (YYYY-MM-DD).

    Returns:
        JSON-Objekt mit Schlüsseln ``mitarbeiter_id_datum`` → ``inhalt``.
    """
    von = request.args.get('von')
    bis = request.args.get('bis')
    db = get_db()
    rows = db.execute("""
        SELECT mitarbeiter_id, datum, inhalt
        FROM einsaetze
        WHERE datum >= ? AND datum <= ?
    """, (von, bis)).fetchall()

    result = {}
    for r in rows:
        key = f"{r['mitarbeiter_id']}_{r['datum']}"
        result[key] = r['inhalt'] or ''
    return jsonify(result)


@bp.route('/api/einsaetze', methods=['POST'])
def save_einsatz():
    """Speichere oder lösche einen Einsatz und schreibe einen Historik-Eintrag.

    Ein leerer ``inhalt`` löscht den Einsatz. Alle Änderungen werden in der
    ``aenderungshistorie``-Tabelle protokolliert.

    Returns:
        JSON mit ``ok: true`` bei Erfolg oder Fehlermeldung.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if 'mitarbeiter_id' not in data or 'datum' not in data:
        return jsonify({"error": "mitarbeiter_id and datum required"}), 422
    ip = get_client_ip()
    db = get_db()

    mid = data['mitarbeiter_id']
    datum = data['datum']
    inhalt = data.get('inhalt', '').strip()

    if len(inhalt) > MAX_INHALT_LEN:
        return jsonify({"error": f"inhalt darf maximal {MAX_INHALT_LEN} Zeichen lang sein"}), 422

    old_row = db.execute(
        "SELECT inhalt FROM einsaetze WHERE mitarbeiter_id=? AND datum=?",
        (mid, datum)
    ).fetchone()
    wert_vorher = old_row['inhalt'] if old_row else ''

    if inhalt:
        db.execute("""
            INSERT INTO einsaetze (mitarbeiter_id, datum, inhalt)
            VALUES (?, ?, ?)
            ON CONFLICT(mitarbeiter_id, datum) DO UPDATE SET inhalt=excluded.inhalt
        """, (mid, datum, inhalt))
    else:
        db.execute("DELETE FROM einsaetze WHERE mitarbeiter_id=? AND datum=?", (mid, datum))

    bearbeiter = str(data.get('bearbeiter_name', 'Unbekannt'))[:MAX_NAME_LEN]
    ma_row = db.execute("SELECT name FROM mitarbeiter WHERE id=?", (mid,)).fetchone()
    ma_name = ma_row['name'] if ma_row else str(mid)

    db.execute("""
        INSERT INTO aenderungshistorie
            (bearbeiter_name, bearbeiter_ip, mitarbeiter_id, mitarbeiter_name, datum, wert_vorher, wert_nachher)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (bearbeiter, ip, mid, ma_name, datum, wert_vorher or '', inhalt))

    db.commit()
    return jsonify({"ok": True})


# ─── FEIERTAGE ────────────────────────────────────────────────────────────────

@bp.route('/api/feiertage')
def get_feiertage():
    """Gib alle Feiertage für ein Jahr zurück.

    Query-Parameter:
        year: Kalenderjahr (Standard: aktuelles Jahr).

    Returns:
        JSON-Array mit allen Feiertags-Datensätzen.
    """
    year = request.args.get('year', date.today().year, type=int)
    db = get_db()
    rows = db.execute(
        "SELECT * FROM feiertage WHERE datum LIKE ? ORDER BY datum",
        (f"{year}%",)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.route('/api/feiertage', methods=['POST'])
def add_feiertag():
    """Füge einen neuen manuellen Feiertag hinzu.

    Returns:
        JSON mit ``ok: true`` bei Erfolg oder Fehlermeldung.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if not data.get('datum') or not data.get('bezeichnung'):
        return jsonify({"error": "datum and bezeichnung required"}), 422
    bezeichnung = str(data['bezeichnung']).strip()
    if len(bezeichnung) > MAX_BEZEICHNUNG_LEN:
        return jsonify({"error": f"bezeichnung darf maximal {MAX_BEZEICHNUNG_LEN} Zeichen lang sein"}), 422
    try:
        datetime.strptime(str(data['datum']), '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "datum muss das Format YYYY-MM-DD haben"}), 422
    db = get_db()
    try:
        db.execute(
            "INSERT INTO feiertage (datum, bezeichnung, automatisch) VALUES (?, ?, 0)",
            (data['datum'], bezeichnung)
        )
        db.commit()
        return jsonify({"ok": True})
    except sqlite3.IntegrityError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route('/api/feiertage/<int:fid>', methods=['DELETE'])
def delete_feiertag(fid: int):
    """Lösche einen Feiertag anhand seiner ID.

    Args:
        fid: Datenbank-ID des zu löschenden Feiertags.

    Returns:
        JSON mit ``ok: true``.
    """
    db = get_db()
    db.execute("DELETE FROM feiertage WHERE id=?", (fid,))
    db.commit()
    return jsonify({"ok": True})


@bp.route('/api/feiertage/generieren', methods=['POST'])
def generiere_feiertage():
    """Generiere Hamburger Feiertage für ein Jahr und füge sie ein.

    Returns:
        JSON mit ``ok: true`` und ``count`` der verarbeiteten Einträge.
    """
    data = request.json or {}
    year = data.get('year', date.today().year)
    db = get_db()
    count = 0
    for datum, name in get_hamburg_holidays(year):
        try:
            db.execute(
                "INSERT OR IGNORE INTO feiertage (datum, bezeichnung, automatisch) VALUES (?, ?, 1)",
                (datum.isoformat(), name)
            )
            count += 1
        except sqlite3.Error:
            pass  # Duplikat – ignorieren
    db.commit()
    return jsonify({"ok": True, "count": count})


# ─── HISTORIE ─────────────────────────────────────────────────────────────────

@bp.route('/api/historie')
def get_historie():
    """Gib gefilterte Einträge aus der Änderungshistorie zurück.

    Query-Parameter:
        limit: Maximale Anzahl Ergebnisse (Standard 200).
        mitarbeiter_id: Filter nach Mitarbeiter-ID.
        bearbeiter: Teilstring-Filter auf Bearbeitername (LIKE).
        von: Startdatum der Änderung (YYYY-MM-DD).
        bis: Enddatum der Änderung (YYYY-MM-DD).

    Returns:
        JSON-Array der Historik-Einträge, absteigend nach Zeitstempel.
    """
    limit = request.args.get('limit', 200, type=int)
    mitarbeiter_id = request.args.get('mitarbeiter_id', type=int)
    bearbeiter = request.args.get('bearbeiter')
    von = request.args.get('von')
    bis = request.args.get('bis')
    db = get_db()

    sql = "SELECT * FROM aenderungshistorie WHERE 1=1"
    params: list = []
    if mitarbeiter_id:
        sql += " AND mitarbeiter_id=?"
        params.append(mitarbeiter_id)
    if bearbeiter:
        sql += " AND bearbeiter_name LIKE ?"
        params.append(f"%{bearbeiter}%")
    if von:
        sql += " AND date(zeitstempel) >= ?"
        params.append(von)
    if bis:
        sql += " AND date(zeitstempel) <= ?"
        params.append(bis)

    sql += " ORDER BY zeitstempel DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ─── CSV-EXPORT ───────────────────────────────────────────────────────────────

@bp.route('/api/export/csv')
def export_csv():
    """Exportiere alle Einsätze eines Jahres als CSV-Datei.

    Query-Parameter:
        year: Kalenderjahr (Standard: aktuelles Jahr).

    Returns:
        CSV-Dateidownload mit Spalten Mitarbeiter, Gruppe, Datum, Inhalt.
    """
    year = request.args.get('year', date.today().year, type=int)
    db = get_db()

    rows = db.execute("""
        SELECT m.name as mitarbeiter, m.gruppe, e.datum, e.inhalt
        FROM einsaetze e
        JOIN mitarbeiter m ON m.id = e.mitarbeiter_id
        WHERE e.datum LIKE ?
        ORDER BY m.gruppe, m.name, e.datum
    """, (f"{year}%",)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Mitarbeiter', 'Gruppe', 'Datum', 'Inhalt'])
    for r in rows:
        writer.writerow([r['mitarbeiter'], r['gruppe'], r['datum'], r['inhalt'] or ''])

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=einsaetze_{year}.csv'}
    )


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@bp.route('/api/health')
def health():
    """Prüfe den Anwendungs- und Datenbankstatus.

    Returns:
        JSON mit ``status: ok`` oder ``status: error`` plus Details.
    """
    try:
        get_db().execute("SELECT 1").fetchone()
        return jsonify({"status": "ok", "db": "connected"})
    except sqlite3.Error as exc:
        return jsonify({"status": "error", "detail": str(exc)}), 500
