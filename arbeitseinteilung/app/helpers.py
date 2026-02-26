from datetime import date, timedelta


def easter(year):
    """Gauss'sche Osterformel"""
    a = year % 19
    b = year % 4
    c = year % 7
    k = year // 100
    p = (13 + 8 * k) // 25
    q = k // 4
    m = (15 - p + k - q) % 30
    n = (4 + k - q) % 7
    d = (19 * a + m) % 30
    e = (2 * b + 4 * c + 6 * d + n) % 7
    if d == 29 and e == 6:
        return date(year, 4, 19)
    if d == 28 and e == 6 and a > 10:
        return date(year, 4, 18)
    return date(year, 3, 22) + timedelta(days=d + e)


def get_hamburg_holidays(year):
    """Gibt alle Hamburger Feiertage für ein Jahr zurück."""
    e = easter(year)
    holidays = [
        (date(year, 1, 1),  "Neujahr"),
        (e - timedelta(days=2), "Karfreitag"),
        (e,                  "Ostersonntag"),
        (e + timedelta(days=1), "Ostermontag"),
        (date(year, 5, 1),  "Tag der Arbeit"),
        (e + timedelta(days=39), "Christi Himmelfahrt"),
        (e + timedelta(days=49), "Pfingstsonntag"),
        (e + timedelta(days=50), "Pfingstmontag"),
        (date(year, 10, 3), "Tag der deutschen Einheit"),
        (date(year, 10, 31), "Reformationstag"),
        (date(year, 12, 24), "Heiligabend"),
        (date(year, 12, 25), "1. Weihnachtstag"),
        (date(year, 12, 26), "2. Weihnachtstag"),
        (date(year, 12, 31), "Silvester"),
    ]
    return holidays


SONDERTAG_FARBEN = {
    "Urlaub":          {"bg": "#FFF176", "text": "#5D4037"},
    "Krank":           {"bg": "#EF9A9A", "text": "#B71C1C"},
    "Schule":          {"bg": "#90CAF9", "text": "#0D47A1"},
    "Innung":          {"bg": "#FFCC80", "text": "#E65100"},
    "Überstd.":        {"bg": "#A5D6A7", "text": "#1B5E20"},
    "KUG":             {"bg": "#CFD8DC", "text": "#37474F"},
    "P":               {"bg": "#B3E5FC", "text": "#01579B"},
    "Mutterschutz":    {"bg": "#F8BBD9", "text": "#880E4F"},
    "Q":               {"bg": "#CE93D8", "text": "#4A148C"},
    "Feiertag":        {"bg": "#B0BEC5", "text": "#263238"},
    "Krank wg. Kind":  {"bg": "#FFAB91", "text": "#BF360C"},
    "MA Gespräch":     {"bg": "#B2DFDB", "text": "#004D40"},
    "Schulung":        {"bg": "#C8E6C9", "text": "#2E7D32"},
    "Berufschule":     {"bg": "#90CAF9", "text": "#0D47A1"},
}

GRUPPEN_REIHENFOLGE = ["KD", "ST", "KDF", "MT", "P1", "P2", "Büro"]

GRUPPEN_FARBEN = {
    "KD":   "#1565C0",
    "ST":   "#2E7D32",
    "KDF":  "#6A1B9A",
    "MT":   "#E65100",
    "P1":   "#00695C",
    "P2":   "#558B2F",
    "Büro": "#4E342E",
}
