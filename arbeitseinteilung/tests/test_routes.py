import pytest
import json


# ─── Bestehende Tests ─────────────────────────────────────────────────────────

def test_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'


def test_get_mitarbeiter(client):
    response = client.get('/api/mitarbeiter')
    assert response.status_code == 200
    assert 'gruppen' in response.json


# ─── Sicherheitsheader ────────────────────────────────────────────────────────

def test_security_headers(client):
    res = client.get('/api/health')
    assert res.headers.get('X-Frame-Options') == 'DENY'
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert res.headers.get('X-XSS-Protection') == '1; mode=block'


# ─── Mitarbeiter ──────────────────────────────────────────────────────────────

def _create_ma(client, name='Test MA', gruppe='KD'):
    res = client.post('/api/mitarbeiter',
                      json={'name': name, 'gruppe': gruppe},
                      content_type='application/json')
    assert res.status_code == 200
    return res.json['id']


def test_create_mitarbeiter(client):
    mid = _create_ma(client, 'Hans Muster')
    assert isinstance(mid, int)


def test_create_mitarbeiter_name_too_long(client):
    res = client.post('/api/mitarbeiter',
                      json={'name': 'X' * 101, 'gruppe': 'KD'},
                      content_type='application/json')
    assert res.status_code == 422


def test_create_mitarbeiter_missing_name(client):
    res = client.post('/api/mitarbeiter',
                      json={'gruppe': 'KD'},
                      content_type='application/json')
    assert res.status_code == 422


# ─── Einsätze – CRUD ─────────────────────────────────────────────────────────

def test_save_einsatz(client):
    mid = _create_ma(client)

    # Speichern
    res = client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid,
        'datum': '2026-03-01',
        'inhalt': 'Baustelle A',
        'bearbeiter_name': 'Admin'
    }, content_type='application/json')
    assert res.status_code == 200
    assert res.json['ok'] is True

    # Abrufen
    res = client.get('/api/einsaetze?von=2026-03-01&bis=2026-03-01')
    assert res.status_code == 200
    assert res.json.get(f'{mid}_2026-03-01') == 'Baustelle A'


def test_save_einsatz_overwrite(client):
    mid = _create_ma(client, 'Overwrite Test')

    client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid, 'datum': '2026-03-02',
        'inhalt': 'Alt', 'bearbeiter_name': 'Admin'
    }, content_type='application/json')

    client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid, 'datum': '2026-03-02',
        'inhalt': 'Neu', 'bearbeiter_name': 'Admin'
    }, content_type='application/json')

    res = client.get('/api/einsaetze?von=2026-03-02&bis=2026-03-02')
    assert res.json.get(f'{mid}_2026-03-02') == 'Neu'


def test_save_einsatz_delete_empty(client):
    mid = _create_ma(client, 'Delete Test')

    client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid, 'datum': '2026-03-03',
        'inhalt': 'Zu löschen', 'bearbeiter_name': 'Admin'
    }, content_type='application/json')

    # Leerer inhalt → löscht den Eintrag
    client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid, 'datum': '2026-03-03',
        'inhalt': '', 'bearbeiter_name': 'Admin'
    }, content_type='application/json')

    res = client.get('/api/einsaetze?von=2026-03-03&bis=2026-03-03')
    assert f'{mid}_2026-03-03' not in res.json


def test_save_einsatz_too_long(client):
    mid = _create_ma(client, 'Length Test')
    res = client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid, 'datum': '2026-03-04',
        'inhalt': 'X' * 501, 'bearbeiter_name': 'Admin'
    }, content_type='application/json')
    assert res.status_code == 422


def test_save_einsatz_missing_fields(client):
    res = client.post('/api/einsaetze', json={'inhalt': 'Test'},
                      content_type='application/json')
    assert res.status_code == 422


# ─── Feiertage ───────────────────────────────────────────────────────────────

def test_add_feiertag(client):
    res = client.post('/api/feiertage', json={
        'datum': '2026-06-15', 'bezeichnung': 'Testtag'
    }, content_type='application/json')
    assert res.status_code == 200

    res = client.get('/api/feiertage?year=2026')
    namen = [f['bezeichnung'] for f in res.json]
    assert 'Testtag' in namen


def test_add_feiertag_invalid_date(client):
    res = client.post('/api/feiertage', json={
        'datum': 'kein-datum', 'bezeichnung': 'Test'
    }, content_type='application/json')
    assert res.status_code == 422


def test_feiertag_bezeichnung_too_long(client):
    res = client.post('/api/feiertage', json={
        'datum': '2026-07-01', 'bezeichnung': 'X' * 201
    }, content_type='application/json')
    assert res.status_code == 422


def test_feiertag_generieren(client):
    res = client.post('/api/feiertage/generieren',
                      json={'year': 2027},
                      content_type='application/json')
    assert res.status_code == 200
    assert 'count' in res.json

    res = client.get('/api/feiertage?year=2027')
    namen = [f['bezeichnung'] for f in res.json]
    assert 'Neujahr' in namen


# ─── CSV-Export ───────────────────────────────────────────────────────────────

def test_csv_export(client):
    mid = _create_ma(client, 'Export Test')
    client.post('/api/einsaetze', json={
        'mitarbeiter_id': mid, 'datum': '2026-05-04',
        'inhalt': 'Exporter Baustelle', 'bearbeiter_name': 'Admin'
    }, content_type='application/json')

    res = client.get('/api/export/csv?year=2026')
    assert res.status_code == 200
    assert 'text/csv' in res.content_type
    body = res.data.decode('utf-8')
    assert 'Exporter Baustelle' in body
    assert 'Mitarbeiter' in body  # Header-Zeile
