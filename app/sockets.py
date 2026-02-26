from . import socketio
from flask_socketio import emit, broadcast
from flask import request

# Tracks which cells are currently being edited: key = "mid_datum" → {sid, name}
locked_cells = {}


@socketio.on('connect')
def on_connect():
    pass


@socketio.on('disconnect')
def on_disconnect():
    # Release all locks held by this client
    to_release = [k for k, v in locked_cells.items() if v['sid'] == request.sid]
    for key in to_release:
        del locked_cells[key]
        emit('cell_unlocked', {'key': key}, broadcast=True)


@socketio.on('cell_lock')
def on_cell_lock(data):
    key = data.get('key')
    name = data.get('name', 'Jemand')
    if key in locked_cells and locked_cells[key]['sid'] != request.sid:
        emit('cell_lock_denied', {'key': key, 'locked_by': locked_cells[key]['name']})
        return
    locked_cells[key] = {'sid': request.sid, 'name': name}
    emit('cell_locked', {'key': key, 'name': name}, broadcast=True, include_self=False)


@socketio.on('cell_unlock')
def on_cell_unlock(data):
    key = data.get('key')
    if key in locked_cells and locked_cells[key]['sid'] == request.sid:
        del locked_cells[key]
        emit('cell_unlocked', {'key': key}, broadcast=True)


@socketio.on('cell_saved')
def on_cell_saved(data):
    # Broadcast the new value to all other clients
    key = data.get('key')
    if key in locked_cells and locked_cells[key]['sid'] == request.sid:
        del locked_cells[key]
    emit('cell_updated', data, broadcast=True, include_self=False)
