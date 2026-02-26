def test_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'

def test_get_mitarbeiter(client):
    response = client.get('/api/mitarbeiter')
    assert response.status_code == 200
    assert 'gruppen' in response.json
