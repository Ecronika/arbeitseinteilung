def test_socket_connection(socket_client):
    assert socket_client.is_connected()


def test_cell_lock(app):
    """cell_lock broadcast wird von einem anderen Client empfangen (include_self=False)."""
    from app import socketio
    client1 = socketio.test_client(app)
    client2 = socketio.test_client(app)

    client1.emit('cell_lock', {'key': '1_2024-01-01', 'name': 'TestUser'})
    # client2 soll das Broadcast-Event empfangen, nicht client1 selbst
    received = client2.get_received()
    assert any(r['name'] == 'cell_locked' for r in received)

    client1.disconnect()
    client2.disconnect()


def test_cell_unlock(socket_client):
    key = '1_2024-01-15'
    socket_client.emit('cell_lock', {'key': key, 'name': 'Locker'})
    socket_client.get_received()  # bestehende Nachrichten leeren

    socket_client.emit('cell_unlock', {'key': key})
    received = socket_client.get_received()
    assert any(r['name'] == 'cell_unlocked' for r in received)


def test_cell_lock_denied(app):
    """Zwei Clients versuchen dieselbe Zelle zu sperren – zweiter wird abgewiesen."""
    from app import socketio

    client1 = socketio.test_client(app)
    client2 = socketio.test_client(app)

    key = '42_2024-06-01'
    client1.emit('cell_lock', {'key': key, 'name': 'UserA'})
    client1.get_received()

    client2.emit('cell_lock', {'key': key, 'name': 'UserB'})
    received2 = client2.get_received()
    assert any(r['name'] == 'cell_lock_denied' for r in received2)

    client1.disconnect()
    client2.disconnect()
