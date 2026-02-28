"""WebSocket-Ereignishandler für kollaborative Zellensperrung und Live-Updates."""

from flask import request
from flask_socketio import emit

from . import socketio

# Tracks welche Zellen gerade bearbeitet werden: key="mid_datum" → {sid, name}
locked_cells: dict = {}


@socketio.on('connect')
def on_connect() -> None:
    """Behandle neue Socket.IO-Verbindung."""


@socketio.on('disconnect')
def on_disconnect() -> None:
    """Gib alle Zellsperren frei, die dieser Client hält.

    Wird automatisch aufgerufen wenn die WebSocket-Verbindung getrennt wird.
    Sendet für jede freigegeben Zelle ein ``cell_unlocked``-Event an alle Clients.
    """
    to_release = [k for k, v in locked_cells.items() if v['sid'] == request.sid]
    for key in to_release:
        del locked_cells[key]
        emit('cell_unlocked', {'key': key}, broadcast=True)


@socketio.on('cell_lock')
def on_cell_lock(data: dict) -> None:
    """Versuche eine Zelle für den anfragenden Client zu sperren.

    Wenn die Zelle bereits von einem anderen Client gesperrt ist, wird ein
    ``cell_lock_denied``-Event zurückgesendet. Bei Erfolg erhalten alle anderen
    Clients ein ``cell_locked``-Event.

    Args:
        data: Dict mit ``key`` (Zellen-ID) und ``name`` (Benutzername).
    """
    key = data.get('key')
    name = data.get('name', 'Jemand')
    if key in locked_cells and locked_cells[key]['sid'] != request.sid:
        emit('cell_lock_denied', {'key': key, 'locked_by': locked_cells[key]['name']})
        return
    locked_cells[key] = {'sid': request.sid, 'name': name}
    emit('cell_locked', {'key': key, 'name': name}, broadcast=True, include_self=False)


@socketio.on('cell_unlock')
def on_cell_unlock(data: dict) -> None:
    """Hebe die Zellensperre des anfragenden Clients auf.

    Nur der Client, der die Sperre hält, kann sie aufheben.
    Sendet ein ``cell_unlocked``-Event an alle Clients.

    Args:
        data: Dict mit ``key`` (Zellen-ID der freizugebenden Zelle).
    """
    key = data.get('key')
    if key in locked_cells and locked_cells[key]['sid'] == request.sid:
        del locked_cells[key]
        emit('cell_unlocked', {'key': key}, broadcast=True)


@socketio.on('cell_saved')
def on_cell_saved(data: dict) -> None:
    """Verarbeite eine gespeicherte Zelle und benachrichtige alle anderen Clients.

    Hebt die Zellensperre auf und sendet den neuen Zellinhalt als
    ``cell_updated``-Event an alle anderen verbundenen Clients.

    Args:
        data: Dict mit ``key``, ``mid``, ``datum`` und ``inhalt``.
    """
    key = data.get('key')
    if key in locked_cells and locked_cells[key]['sid'] == request.sid:
        del locked_cells[key]
    emit('cell_updated', data, broadcast=True, include_self=False)
