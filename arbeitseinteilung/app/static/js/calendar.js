// ─── Kalender ─────────────────────────────────────────────────────────────────

// Sicheres Rendering-Flag gegen Doppel-Submit
let _saving = false;

const TAGE_KURZ = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
const MONATE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];

let calYear = new Date().getFullYear();
let allDays = [];      // Array of Date objects for the year
let feiertage = {};      // 'YYYY-MM-DD' → bezeichnung
let einsaetze = {};      // 'mid_datum' → inhalt
let mitarbeiter = {};      // { gruppen: {...}, alle: [...] }

// Popup state
let popupMid = null;
let popupDatum = null;
let popupKey = null;

// ─── Boot ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // Warte bis App geladen (app.js)
    await waitFor(() => typeof alleMitarbeiter !== 'undefined' && alleMitarbeiter.length > 0, 2000);

    buildDayArray();
    const [, maOk] = await Promise.all([loadFeiertage(), loadMitarbeiter()]);
    await loadEinsaetze();
    if (maOk !== false) renderCalendar();

    // Verwende Event Delegation für alle Kalenderzellen statt 18.000 einzelner Listener
    document.getElementById('calendarBody').addEventListener('click', e => {
        const td = e.target.closest('td.day-col');
        if (td) onCellClick({ currentTarget: td });
    });

    document.getElementById('calendarBody').addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            const td = e.target.closest('td.day-col');
            if (td) onCellClick({ currentTarget: td });
        }
    });

    const yearDisp = document.getElementById('currentYearDisplay');
    if (yearDisp) yearDisp.textContent = calYear;
    scrollToToday();
    setupSocketListeners();
    setupDatePicker();
    buildSondertageGrid();
    setupOutsideClick();
});

function waitFor(fn, timeout) {
    return new Promise(resolve => {
        const start = Date.now();
        const check = () => {
            if (fn() || Date.now() - start > timeout) resolve();
            else setTimeout(check, 50);
        };
        check();
    });
}

// ─── Daten laden ──────────────────────────────────────────────────────────────

function buildDayArray() {
    allDays = [];
    const d = new Date(calYear, 0, 1);
    while (d.getFullYear() === calYear) {
        allDays.push(new Date(d));
        d.setDate(d.getDate() + 1);
    }
}

async function loadFeiertage() {
    try {
        const res = await fetch(`/api/feiertage?year=${calYear}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        feiertage = {};
        data.forEach(f => { feiertage[f.datum] = { bezeichnung: f.bezeichnung, halbtag: f.halbtag }; });
    } catch (e) {
        console.error('Feiertage laden fehlgeschlagen', e);
        feiertage = {};
    }
}

async function loadMitarbeiter() {
    try {
        const res = await fetch('/api/mitarbeiter');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        mitarbeiter = await res.json();
        return true;
    } catch (e) {
        console.error('Mitarbeiter laden fehlgeschlagen', e);
        document.getElementById('calendarBody').innerHTML =
            `<tr><td colspan="999" style="padding:20px;text-align:center;color:#c62828">
             ⚠ Mitarbeiter konnten nicht geladen werden. Bitte Seite neu laden.
             </td></tr>`;
        return false;
    }
}

async function loadEinsaetze() {
    try {
        const von = `${calYear}-01-01`;
        const bis = `${calYear}-12-31`;
        const res = await fetch(`/api/einsaetze?von=${von}&bis=${bis}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        einsaetze = await res.json();
    } catch (e) {
        console.error('Einsätze laden fehlgeschlagen', e);
        showToast('Einsätze konnten nicht geladen werden', 'error');
        einsaetze = {};
    }
}

// ─── Kalender rendern ─────────────────────────────────────────────────────────

function renderCalendar() {
    const head = document.getElementById('calendarHead');
    const body = document.getElementById('calendarBody');
    const today = formatDate(new Date());

    // ─ Header: Monatsnamen ─
    let monthRow = '<tr>';
    // Sticky cols placeholder
    monthRow += `<th class="sticky-col col-nr th-sticky-header" rowspan="2">Nr</th>`;
    monthRow += `<th class="sticky-col col-kfz th-sticky-header" rowspan="2">KFZ / Monteur</th>`;
    monthRow += `<th class="sticky-col col-bd th-sticky-header" rowspan="2">B/D</th>`;
    monthRow += `<th class="sticky-col col-pnr th-sticky-header" rowspan="2">P.Nr</th>`;
    monthRow += `<th class="sticky-col col-name th-sticky-header" rowspan="2">Mitarbeiter</th>`;

    // Monatsspalten
    let currentMonth = -1;
    let monthSpan = 0;
    let monthCells = [];
    allDays.forEach(d => {
        const m = d.getMonth();
        if (m !== currentMonth) {
            if (currentMonth >= 0) monthCells.push({ name: MONATE[currentMonth], span: monthSpan });
            currentMonth = m;
            monthSpan = 1;
        } else { monthSpan++; }
    });
    monthCells.push({ name: MONATE[currentMonth], span: monthSpan });
    monthCells.forEach(mc => {
        monthRow += `<th colspan="${mc.span}" class="th-month" style="left:auto">${mc.name}</th>`;
    });
    monthRow += '</tr>';

    // ─ Header: Tagesnummern ─
    let dayRow = '<tr>';
    allDays.forEach(d => {
        const ds = formatDate(d);
        const dow = d.getDay();
        const isWeekend = dow === 0 || dow === 6;
        const isToday = ds === today;
        const isFeiertag = !!feiertage[ds];
        const feiertagObj = feiertage[ds] || {};
        const isHalbtag = isFeiertag && feiertagObj.halbtag === 1;
        let cls = 'th-day';
        if (isWeekend) cls += ' weekend col-narrow';
        if (isToday) cls += ' is-today';
        if (isFeiertag) cls += ' feiertag';
        if (isHalbtag) cls += ' half-holiday';
        const title = isFeiertag ? ` title="${escapeHtml(feiertagObj.bezeichnung)}"` : '';

        const kwLabel = isMonday
            ? `<div style="font-size:9px;color:#aaa;line-height:1.1;margin:1px 0">KW${getISOWeek(d)}</div>`
            : `<div style="font-size:9px;line-height:1.1;margin:1px 0;visibility:hidden">KW</div>`;

        dayRow += `<th class="${cls}"${title} data-date="${ds}"><div style="font-weight:600">${TAGE_KURZ[dow]}</div>${kwLabel}<div>${d.getDate()}</div></th>`;
    });
    dayRow += '</tr>';

    head.innerHTML = monthRow + dayRow;

    // ─ Body: Mitarbeitergruppen + Zeilen ─
    const GRUPPEN = ['KD', 'ST', 'KDF', 'MT', 'P1', 'P2', 'Büro'];
    let bodyHtml = '';
    const gruppen = mitarbeiter.gruppen || {};

    GRUPPEN.forEach(g => {
        const members = gruppen[g];
        if (!members || members.length === 0) return;

        const farbe = GRUPPEN_FARBEN[g] || '#555';
        const totalCols = allDays.length + 5;
        bodyHtml += `<tr class="group-row" style="--group-bg:${farbe}">
            <td colspan="${totalCols}">${g}</td>
        </tr>`;

        members.forEach(ma => {
            bodyHtml += buildMitarbeiterRow(ma, today);
        });
    });

    if (!bodyHtml) {
        bodyHtml = `<tr><td colspan="999" style="padding:40px;text-align:center;color:var(--muted);font-style:italic">
             👥 Keine Mitarbeiter in der Datenbank gefunden. Bitte legen Sie unter 'Mitarbeiter' welche an.
             </td></tr>`;
    }
    body.innerHTML = bodyHtml;

    // Event Listener werden jetzt via Delegation im DOMContentLoaded gebunden
}

function buildMitarbeiterRow(ma, today) {
    // KFZ-Anzeige
    let kfzDisplay = '';
    if (ma.typ === 'Azubi' || ma.typ === 'Praktikant' || ma.typ === 'Leiharbeiter') {
        kfzDisplay = ma.betreuer_name || ma.verleihfirma || '';
    } else {
        kfzDisplay = ma.kennzeichen || '';
    }

    // Kraftstoff-Anzeige
    let bdDisplay = '';
    if (ma.baujahr && ma.kraftstoff) {
        bdDisplay = `${ma.baujahr}/${ma.kraftstoff}`;
    }

    // Name-Anzeige mit Badges
    let nameDisplay = escapeHtml(ma.name);
    if (ma.fuehrerschein) nameDisplay += ' <span style="font-size:10px;color:#888">F</span>';
    if (ma.azubi_block) nameDisplay += ` <span style="font-size:10px;background:#e3f2fd;color:#1565C0;border-radius:3px;padding:1px 4px">${escapeHtml(ma.azubi_block)}</span>`;
    if (ma.verleihfirma) nameDisplay += ` <span style="font-size:10px;color:#aaa">(${escapeHtml(ma.verleihfirma)})</span>`;

    // Visual Hints (MEDIUM-3)
    if (ma.typ === 'Azubi') nameDisplay += ' <span style="font-size:10px;color:var(--accent);border:1px solid var(--accent);border-radius:3px;padding:0 3px;margin-left:4px">A</span>';
    if (ma.typ === 'Leiharbeiter') nameDisplay += ' <span style="font-size:10px;color:var(--muted);border:1px solid var(--muted);border-radius:3px;padding:0 3px;margin-left:4px">L</span>';

    let row = `<tr data-mid="${ma.id}">
        <td class="sticky-col col-nr">${ma.id}</td>
        <td class="sticky-col col-kfz" title="${escapeHtml(kfzDisplay)}">${escapeHtml(kfzDisplay)}</td>
        <td class="sticky-col col-bd">${escapeHtml(bdDisplay)}</td>
        <td class="sticky-col col-pnr">${escapeHtml(ma.personalnummer || '')}</td>
        <td class="sticky-col col-name">${nameDisplay}</td>`;

    allDays.forEach(d => {
        const ds = formatDate(d);
        const key = `${ma.id}_${ds}`;
        const inhalt = einsaetze[key] || '';
        const dow = d.getDay();
        const isWeekend = dow === 0 || dow === 6;
        const isToday = ds === today;
        const isFeiertag = !!feiertage[ds];
        const feiertagObj = feiertage[ds] || {};
        const isHalbtag = isFeiertag && feiertagObj.halbtag === 1;

        const { bg, text } = getCellStyle(inhalt, isFeiertag, feiertagObj.bezeichnung);

        let cls = 'day-col';
        if (isWeekend) cls += ' weekend col-narrow';
        if (isToday) cls += ' is-today';
        if (isFeiertag && !inhalt) cls += ' feiertag';
        if (isHalbtag) cls += ' half-holiday';

        const displayText = isFeiertag && !inhalt ? escapeHtml(feiertagObj.bezeichnung) : escapeHtml(inhalt);

        row += `<td class="${cls}" data-mid="${ma.id}" data-date="${ds}" data-key="${key}" tabindex="0"
                    style="background:${bg};color:${text}"
                    title="${isFeiertag && !inhalt ? escapeHtml(feiertagObj.bezeichnung) : escapeHtml(inhalt)}">${displayText}</td>`;
    });

    row += '</tr>';
    return row;
}

function getCellStyle(inhalt, isFeiertag, feiertagName) {
    if (!inhalt && isFeiertag) return { bg: '#eceff1', text: '#546e7a' };
    if (!inhalt) return { bg: 'transparent', text: 'var(--text)' };

    // Sondertag prüfen
    for (const [key, farbe] of Object.entries(SONDERTAG_FARBEN)) {
        if (inhalt.toLowerCase().startsWith(key.toLowerCase())) {
            return { bg: farbe.bg, text: farbe.text };
        }
    }
    return { bg: '#e8f0fe', text: '#1a56db' };
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function scrollToToday() {
    const today = formatDate(new Date());
    const th = document.querySelector(`th[data-date="${today}"]`);
    if (th) {
        const scroll = document.getElementById('calendarScroll');
        const offset = th.offsetLeft - window.innerWidth / 2 + 100;
        scroll.scrollLeft = Math.max(0, offset);
    }
}

function scrollToDate(dateStr) {
    if (!dateStr) return;
    const th = document.querySelector(`th[data-date="${dateStr}"]`);
    if (th) {
        const scroll = document.getElementById('calendarScroll');
        const offset = th.offsetLeft - window.innerWidth / 2 + 100;
        scroll.scrollLeft = Math.max(0, offset);
    }
}

function setupDatePicker() {
    const dp = document.getElementById('datePicker');
    if (dp) {
        dp.value = formatDate(new Date());
        dp.min = `${calYear}-01-01`;
        dp.max = `${calYear}-12-31`;
    }
}

// ─── Popup ────────────────────────────────────────────────────────────────────

function onCellClick(e) {
    const td = e.currentTarget;
    if (td.classList.contains('cell-locked')) {
        const lockerName = td.dataset.locker || 'jemand anderem';
        showToast(`Diese Zelle wird aktuell von ${lockerName} bearbeitet`, 'error');
        return;
    }

    if (popupKey && popupKey !== td.dataset.key) {
        if (socket) socket.emit('cell_unlock', { key: popupKey });
    }

    lastFocusedElement = td; // global aus app.js
    popupMid = parseInt(td.dataset.mid);
    popupDatum = td.dataset.date;
    popupKey = td.dataset.key;

    const isFeiertag = !!feiertage[popupDatum];
    const ma = (mitarbeiter.alle || []).find(m => m.id === popupMid);
    const maName = ma ? ma.name : `MA ${popupMid}`;

    // Datum formatieren
    const d = parseDate(popupDatum);
    const dateLabel = `${TAGE_KURZ[d.getDay()]}. ${d.getDate()}. ${MONATE[d.getMonth()]} – ${maName}`;

    document.getElementById('popupHeader').textContent = dateLabel;
    document.getElementById('popupInput').value = einsaetze[popupKey] || '';

    // Feiertag-Info falls vorhanden
    if (isFeiertag) {
        document.getElementById('popupInput').placeholder = (feiertage[popupDatum]?.bezeichnung || 'Feiertag') + ' (Feiertag)';
    } else {
        document.getElementById('popupInput').placeholder = 'Baustelle / Einsatzort...';
    }

    positionPopup(td);
    document.getElementById('cellPopup').style.display = 'block';
    // Azubi Kürzel Hint inyectieren
    let hintDiv = document.getElementById('azubiHint');
    if (!hintDiv) {
        hintDiv = document.createElement('div');
        hintDiv.id = 'azubiHint';
        const gridNode = document.getElementById('sondertageGrid');
        gridNode.parentNode.insertBefore(hintDiv, gridNode);
    }
    if (ma && ma.typ === 'Azubi') {
        const bName = ma.betreuer_name || '';
        const bInitials = bName.split(' ').map(n => n[0]).join('').toUpperCase();
        const shortcutStr = `${ma.gruppe} ${bInitials}`;
        hintDiv.innerHTML = `<button type="button" class="sondertag-btn" style="width:100%;margin-bottom:8px;background:#e3f2fd;color:#1565c0" onclick="setSondertag('${shortcutStr}')">Azubi-Kürzel: ${shortcutStr}</button>`;
    } else {
        hintDiv.innerHTML = '';
    }

    document.getElementById('popupInput').focus();

    // Zelle sperren
    if (socket && currentUser.name) {
        socket.emit('cell_lock', { key: popupKey, name: currentUser.name });
    }
}

function positionPopup(td) {
    const popup = document.getElementById('cellPopup');
    const rect = td.getBoundingClientRect();
    const vh = window.innerHeight;
    const vw = window.innerWidth;

    let top = rect.bottom + 4;
    let left = rect.left;

    popup.style.display = 'block';
    const pw = popup.offsetWidth;
    const ph = popup.offsetHeight;

    if (top + ph > vh - 10) top = rect.top - ph - 4;
    if (left + pw > vw - 10) left = vw - pw - 10;
    if (left < 10) left = 10;

    popup.style.top = `${top}px`;
    popup.style.left = `${left}px`;
}

function closePopup() {
    document.getElementById('cellPopup').style.display = 'none';
    if (socket && popupKey) {
        socket.emit('cell_unlock', { key: popupKey });
    }
    popupMid = null; popupDatum = null; popupKey = null;

    if (lastFocusedElement) lastFocusedElement.focus();
}

function clearCell() {
    document.getElementById('popupInput').value = '';
    saveCell();
}

async function saveCell() {
    if (!popupMid || !popupDatum || _saving) { if (!_saving) closePopup(); return; }
    _saving = true;

    const btnSave = document.querySelector('.btn-save');
    if (btnSave) btnSave.disabled = true;

    const inhalt = document.getElementById('popupInput').value.trim();

    try {
        const response = await fetch('/api/einsaetze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mitarbeiter_id: popupMid,
                datum: popupDatum,
                inhalt: inhalt,
                bearbeiter_name: currentUser.name || 'Unbekannt'
            })
        });

        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);

        // Lokal aktualisieren
        const key = popupKey;
        einsaetze[key] = inhalt;
        updateCell(popupMid, popupDatum, inhalt);

        // Andere Clients benachrichtigen
        if (socket) {
            socket.emit('cell_saved', {
                key: key,
                mid: popupMid,
                datum: popupDatum,
                inhalt: inhalt
            });
        }

        showToast('Gespeichert', 'success');
    } catch (e) {
        showToast('Fehler beim Speichern', 'error');
        return;
    } finally {
        if (btnSave) btnSave.disabled = false;
        _saving = false;
    }

    closePopup();
}

function updateCell(mid, datum, inhalt) {
    const td = document.querySelector(`td[data-key="${mid}_${datum}"]`);
    if (!td) return;

    const isFeiertag = !!feiertage[datum];
    const feiertagObj = feiertage[datum] || {};
    const { bg, text } = getCellStyle(inhalt, isFeiertag, feiertagObj.bezeichnung);
    td.style.background = bg;
    td.style.color = text;

    const displayText = isFeiertag && !inhalt ? feiertagObj.bezeichnung : inhalt;
    td.textContent = displayText || (isFeiertag ? feiertagObj.bezeichnung : '');
    td.title = inhalt || (isFeiertag ? feiertagObj.bezeichnung : '');
}

// ─── Socket.IO Live-Updates ───────────────────────────────────────────────────

function setupSocketListeners() {
    if (!socket) return;

    socket.off('cell_locked');
    socket.off('cell_unlocked');
    socket.off('cell_lock_denied');
    socket.off('cell_updated');

    socket.on('cell_locked', ({ key, name }) => {
        const td = document.querySelector(`td[data-key="${key}"]`);
        if (td) {
            td.classList.add('cell-locked');
            td.dataset.locker = name;
        }
    });

    socket.on('cell_unlocked', ({ key }) => {
        const td = document.querySelector(`td[data-key="${key}"]`);
        if (td) {
            td.classList.remove('cell-locked');
            delete td.dataset.locker;
        }
    });

    socket.on('cell_lock_denied', ({ key, locked_by }) => {
        showToast(`Wird gerade von ${locked_by} bearbeitet`, 'error');
        popupMid = null; popupDatum = null; popupKey = null;
        document.getElementById('cellPopup').style.display = 'none';
    });

    socket.on('cell_updated', ({ key, mid, datum, inhalt }) => {
        einsaetze[key] = inhalt;
        updateCell(mid, datum, inhalt);
        const td = document.querySelector(`td[data-key="${key}"]`);
        if (td) {
            td.classList.remove('cell-locked');
            delete td.dataset.locker;
        }
    });
}

// ─── Sondertage-Grid im Popup ─────────────────────────────────────────────────

function buildSondertageGrid() {
    const grid = document.getElementById('sondertageGrid');
    if (!grid) return;
    grid.innerHTML = Object.entries(SONDERTAG_FARBEN).map(([key, farbe]) => `
        <button type="button" class="sondertag-btn"
                style="background:${farbe.bg};color:${farbe.text}"
                onclick="setSondertag('${escapeHtml(key)}')">${escapeHtml(key)}</button>
    `).join('');
}

function setSondertag(kuerzel) {
    document.getElementById('popupInput').value = kuerzel;
    saveCell();
}

async function changeYear(delta) {
    if (_saving) return;
    calYear += delta;
    const yearDisp = document.getElementById('currentYearDisplay');
    if (yearDisp) yearDisp.textContent = calYear;

    setupDatePicker();

    document.getElementById('calendarBody').innerHTML = '<tr><td colspan="999" style="padding:40px;text-align:center">&#10227; Lade Jahr...</td></tr>';

    buildDayArray();
    const [, maOk] = await Promise.all([loadFeiertage(), loadMitarbeiter()]);
    await loadEinsaetze();
    if (maOk !== false) {
        renderCalendar();
        scrollToDate(`${calYear}-01-01`);
    }
}

function getISOWeek(d) {
    const date = new Date(d.getTime());
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
    const week1 = new Date(date.getFullYear(), 0, 4);
    return 1 + Math.round(((date.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
}

// ─── Außerhalb klicken schließt Popup ────────────────────────────────────────

function setupOutsideClick() {
    document.addEventListener('click', e => {
        const popup = document.getElementById('cellPopup');
        if (popup.style.display === 'block' && !popup.contains(e.target) && !e.target.closest('.day-col')) {
            closePopup();
        }
    });

    // Enter speichert
    document.getElementById('popupInput')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') saveCell();
        if (e.key === 'Escape') closePopup();
    });
}
