def test_socket_connection(socket_client):
    assert socket_client.is_connected()
    
def test_cell_lock(socket_client):
    socket_client.emit('cell_lock', {'key': '1_2024-01-01', 'name': 'TestUser'})
    received = socket_client.get_received()
    assert any(r['name'] == 'cell_locked' for r in received)
