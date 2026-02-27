// ─── Globale App-Logik ────────────────────────────────────────────────────────

let currentUser = { id: null, name: null };
let alleMitarbeiter = [];
let socket;
let lastFocusedElement = null;

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // Socket.IO verbinden
    socket = io({ transports: ['websocket', 'polling'] });

    socket.on('connect', () => console.log('Socket verbunden:', socket.id));
    socket.on('disconnect', () => {
        console.warn('Socket getrennt');
        showToast('Verbindung verloren (Offline)', 'error');
    });
    socket.on('reconnect', async () => {
        showToast('Verbindung wiederhergestellt – lade Daten neu…', 'success');
        // Einsätze neu laden damit keine veralteten Daten angezeigt werden.
        // Die Funktion ist in calendar.js definiert und nur auf der Kalender-Seite verfügbar.
        if (typeof loadEinsaetze === 'function' && typeof renderCalendar === 'function') {
            await loadEinsaetze();
            renderCalendar();
        }
    });

    // Mitarbeiterliste laden
    try {
        const res = await fetch('/api/mitarbeiter');
        const data = await res.json();
        alleMitarbeiter = data.alle || [];
        document.dispatchEvent(new CustomEvent('app:mitarbeiterLoaded'));
    } catch (e) { console.error('Mitarbeiter laden fehlgeschlagen', e); }

    // Nutzer aus IP laden
    await ladeAktuellenNutzer();

    const uList = document.getElementById('userList');
    if (uList) {
        uList.addEventListener('click', e => {
            const item = e.target.closest('[data-id]');
            if (item) selectUser(parseInt(item.dataset.id), item.dataset.name);
        });
    }
});

// ─── Nutzeridentifikation ─────────────────────────────────────────────────────

async function ladeAktuellenNutzer() {
    try {
        const res = await fetch('/api/mein-nutzer');
        const data = await res.json();
        if (data.mitarbeiter_id) {
            setCurrentUser(data.mitarbeiter_id, data.name);
        }
        // Modal nur einmal pro Browser-Tab-Session zeigen.
        // sessionStorage wird beim Schließen des Tabs geleert – dadurch
        // erkennt der Nutzer beim nächsten Öffnen wieder, wer er ist.
        const confirmed = sessionStorage.getItem('identityConfirmed');
        if (!confirmed) {
            openUserSelect();
        }
    } catch (e) { openUserSelect(); }
}

function setCurrentUser(id, name) {
    currentUser = { id, name };
    const badge = document.getElementById('userName');
    if (badge) badge.textContent = name;
}

function openUserSelect() {
    lastFocusedElement = document.activeElement;
    renderUserList('');
    document.getElementById('userModal').style.display = 'flex';
    setTimeout(() => document.getElementById('userSearch')?.focus(), 100);
}

function closeUserModal() {
    document.getElementById('userModal').style.display = 'none';
    if (lastFocusedElement) lastFocusedElement.focus();
}

function filterUserList() {
    const q = document.getElementById('userSearch').value;
    renderUserList(q);
}

function renderUserList(query) {
    const list = document.getElementById('userList');
    if (!list) return;
    const filtered = alleMitarbeiter.filter(m =>
        m.name.toLowerCase().includes(query.toLowerCase())
    );
    list.innerHTML = filtered.map(m => `
        <div class="user-list-item" data-id="${m.id}" data-name="${escapeHtml(m.name)}" style="cursor:pointer">
            <div>${escapeHtml(m.name)}</div>
            <div class="item-sub">${escapeHtml(m.gruppe || '')} · ${escapeHtml(m.typ || '')}</div>
        </div>
    `).join('') || '<div class="user-list-item" style="color:#aaa">Keine Treffer</div>';
}

async function selectUser(id, name) {
    setCurrentUser(id, name);
    // Merken, dass der Nutzer in dieser Tab-Session bestätigt hat
    sessionStorage.setItem('identityConfirmed', '1');
    closeUserModal();
    // IP-Zuordnung speichern
    try {
        await fetch('/api/ip-nutzer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mitarbeiter_id: id })
        });
    } catch (e) { /* non-critical */ }
}

// ─── Toast-Benachrichtigungen ─────────────────────────────────────────────────

let toastEl;
function showToast(msg, type = 'success') {
    if (!toastEl) {
        toastEl = document.createElement('div');
        toastEl.className = 'toast';
        toastEl.setAttribute('aria-live', 'polite');
        document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.className = `toast ${type}`;
    void toastEl.offsetWidth; // reflow
    toastEl.classList.add('show');
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(() => toastEl.classList.remove('show'), 2800);
}

// ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        const loginModal = document.getElementById('userModal');
        if (loginModal && loginModal.style.display !== 'none' && (!currentUser || !currentUser.id)) {
            return; // Schließen verhindern, solange kein User gesetzt
        }

        let closed = false;
        const openModals = document.querySelectorAll('.modal-overlay');
        openModals.forEach(m => {
            if (m.style.display && m.style.display !== 'none') {
                m.style.display = 'none';
                closed = true;
            }
        });
        if (closed && lastFocusedElement) {
            lastFocusedElement.focus();
        } else if (closed && document.activeElement !== document.body) {
            document.body.focus();
        }
    }
});

function formatDate(d) {
    // Date object → 'YYYY-MM-DD'
    return d.toISOString().slice(0, 10);
}

function parseDate(s) {
    const [y, m, d] = s.split('-').map(Number);
    return new Date(y, m - 1, d);
}
