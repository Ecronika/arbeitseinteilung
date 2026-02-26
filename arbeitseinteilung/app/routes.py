from flask import Blueprint, jsonify, request, render_template, current_app
from datetime import date, datetime
import json
from .database import get_db
from .helpers import SONDERTAG_FARBEN, GRUPPEN_REIHENFOLGE, GRUPPEN_FARBEN, get_hamburg_holidays

bp = Blueprint('main', __name__)


def get_client_ip():
    return request.remote_addr


# ─── SEITEN ────────────────────────────────────────────────────────────────────

@bp.route('/')
def index():
    return render_template('index.html',
                           sondertag_farben=SONDERTAG_FARBEN,
                           gruppen_farben=GRUPPEN_FARBEN,
                           gruppen_reihenfolge=GRUPPEN_REIHENFOLGE)


@bp.route('/mitarbeiter-verwaltung')
def mitarbeiter_seite():
    return render_template('mitarbeiter.html', gruppen=GRUPPEN_REIHENFOLGE)


@bp.route('/fahrzeuge-verwaltung')
def fahrzeuge_seite():
    return render_template('fahrzeuge.html')


@bp.route('/feiertage-verwaltung')
def feiertage_seite():
    return render_template('feiertage.html')


@bp.route('/historie')
def historie_seite():
    return render_template('historie.html')


# ─── IP / NUTZER ────────────────────────────────────────────────────────────────

@bp.route('/api/mein-nutzer')
def mein_nutzer():
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


# ─── MITARBEITER ────────────────────────────────────────────────────────────────

@bp.route('/api/mitarbeiter')
def get_mitarbeiter():
    db = get_db()
    rows = db.execute("""
        SELECT m.*, f.kennzeichen, f.baujahr, f.kraftstoff,
               b.name as betreuer_name
        FROM mitarbeiter m
        LEFT JOIN fahrzeuge f ON f.mitarbeiter_id = m.id AND f.aktiv = 1
        LEFT JOIN mitarbeiter b ON b.id = m.betreuer_id
        WHERE m.aktiv = 1 AND (m.einsatz_bis IS NULL OR m.einsatz_bis >= date('now', 'localtime'))
        ORDER BY m.gruppe, m.sort_order, m.name
    """).fetchall()

    gruppen = {}
    for g in GRUPPEN_REIHENFOLGE:
        gruppen[g] = []

    for r in rows:
        d = dict(r)
        g = d.get('gruppe', 'KD')
        if g not in gruppen:
            gruppen[g] = []
        gruppen[g].append(d)

    return jsonify({"gruppen": gruppen, "alle": [dict(r) for r in rows]})


@bp.route('/api/mitarbeiter', methods=['POST'])
def create_mitarbeiter():
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if not data.get('name') or not str(data['name']).strip():
        return jsonify({"error": "name required"}), 422
    db = get_db()
    cur = db.execute("""
        INSERT INTO mitarbeiter
            (name, personalnummer, gruppe, typ, fuehrerschein, azubi_block,
             betreuer_id, verleihfirma, einsatz_von, einsatz_bis, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['name'], data.get('personalnummer'), data.get('gruppe', 'KD'),
        data.get('typ', 'Monteur'), 1 if data.get('fuehrerschein') else 0,
        data.get('azubi_block'), data.get('betreuer_id'),
        data.get('verleihfirma'), data.get('einsatz_von'), data.get('einsatz_bis'),
        data.get('sort_order', 0)
    ))
    db.commit()
    return jsonify({"id": cur.lastrowid, "ok": True})


@bp.route('/api/mitarbeiter/<int:mid>', methods=['PUT'])
def update_mitarbeiter(mid):
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if not data.get('name') or not str(data['name']).strip():
        return jsonify({"error": "name required"}), 422
    db = get_db()
    db.execute("""
        UPDATE mitarbeiter SET
            name=?, personalnummer=?, gruppe=?, typ=?, fuehrerschein=?,
            azubi_block=?, betreuer_id=?, verleihfirma=?,
            einsatz_von=?, einsatz_bis=?, sort_order=?, aktiv=?
        WHERE id=?
    """, (
        data['name'], data.get('personalnummer'), data.get('gruppe', 'KD'),
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
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    orders = data.get('orders', [])
    try:
        db = get_db()
        for item in orders:
            db.execute("UPDATE mitarbeiter SET sort_order = ? WHERE id = ?", (item.get('sort_order'), item.get('id')))
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route('/api/mitarbeiter/<int:mid>', methods=['DELETE'])
def deactivate_mitarbeiter(mid):
    db = get_db()
    db.execute("UPDATE mitarbeiter SET aktiv=0 WHERE id=?", (mid,))
    db.commit()
    return jsonify({"ok": True})


# ─── FAHRZEUGE ──────────────────────────────────────────────────────────────────

@bp.route('/api/fahrzeuge')
def get_fahrzeuge():
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
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if not data.get('kennzeichen') or not str(data['kennzeichen']).strip():
        return jsonify({"error": "kennzeichen required"}), 422
    db = get_db()
    cur = db.execute("""
        INSERT INTO fahrzeuge (kennzeichen, baujahr, kraftstoff, status, status_kommentar, mitarbeiter_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data['kennzeichen'], data.get('baujahr'), data.get('kraftstoff', 'D'),
        data.get('status', 'Aktiv'), data.get('status_kommentar'), data.get('mitarbeiter_id')
    ))
    db.commit()
    return jsonify({"id": cur.lastrowid, "ok": True})


@bp.route('/api/fahrzeuge/<int:fid>', methods=['PUT'])
def update_fahrzeug(fid):
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if not data.get('kennzeichen') or not str(data['kennzeichen']).strip():
        return jsonify({"error": "kennzeichen required"}), 422
    db = get_db()
    db.execute("""
        UPDATE fahrzeuge SET
            kennzeichen=?, baujahr=?, kraftstoff=?, status=?,
            status_kommentar=?, mitarbeiter_id=?, aktiv=?
        WHERE id=?
    """, (
        data['kennzeichen'], data.get('baujahr'), data.get('kraftstoff', 'D'),
        data.get('status', 'Aktiv'), data.get('status_kommentar'),
        data.get('mitarbeiter_id'), 1 if data.get('aktiv', True) else 0,
        fid
    ))
    db.commit()
    return jsonify({"ok": True})


# ─── EINSÄTZE ───────────────────────────────────────────────────────────────────

@bp.route('/api/einsaetze')
def get_einsaetze():
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

    # Historik
    bearbeiter = data.get('bearbeiter_name', 'Unbekannt')
    ma_row = db.execute("SELECT name FROM mitarbeiter WHERE id=?", (mid,)).fetchone()
    ma_name = ma_row['name'] if ma_row else str(mid)

    db.execute("""
        INSERT INTO aenderungshistorie
            (bearbeiter_name, bearbeiter_ip, mitarbeiter_id, mitarbeiter_name, datum, wert_vorher, wert_nachher)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (bearbeiter, ip, mid, ma_name, datum, wert_vorher or '', inhalt))

    db.commit()
    return jsonify({"ok": True})


# ─── FEIERTAGE ──────────────────────────────────────────────────────────────────

@bp.route('/api/feiertage')
def get_feiertage():
    year = request.args.get('year', date.today().year, type=int)
    db = get_db()
    rows = db.execute(
        "SELECT * FROM feiertage WHERE datum LIKE ? ORDER BY datum",
        (f"{year}%",)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.route('/api/feiertage', methods=['POST'])
def add_feiertag():
    if not request.is_json:
        return jsonify({"error": "Content-Type: application/json required"}), 415
    data = request.json or {}
    if not data.get('datum') or not data.get('bezeichnung'):
        return jsonify({"error": "datum and bezeichnung required"}), 422
    db = get_db()
    try:
        db.execute(
            "INSERT INTO feiertage (datum, bezeichnung, automatisch) VALUES (?, ?, 0)",
            (data['datum'], data['bezeichnung'])
        )
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route('/api/feiertage/<int:fid>', methods=['DELETE'])
def delete_feiertag(fid):
    db = get_db()
    db.execute("DELETE FROM feiertage WHERE id=?", (fid,))
    db.commit()
    return jsonify({"ok": True})


@bp.route('/api/feiertage/generieren', methods=['POST'])
def generiere_feiertage():
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
        except Exception:
            pass
    db.commit()
    return jsonify({"ok": True, "count": count})


# ─── HISTORIE ────────────────────────────────────────────────────────────────────

@bp.route('/api/historie')
def get_historie():
    limit = request.args.get('limit', 200, type=int)
    mitarbeiter_id = request.args.get('mitarbeiter_id', type=int)
    bearbeiter = request.args.get('bearbeiter')
    von = request.args.get('von')
    bis = request.args.get('bis')
    db = get_db()

    sql = "SELECT * FROM aenderungshistorie WHERE 1=1"
    params = []
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


@bp.route('/api/health')
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
        return jsonify({"status": "ok", "db": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500
