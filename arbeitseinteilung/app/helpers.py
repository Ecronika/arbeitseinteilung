from datetime import date, timedelta
from typing import List, Tuple, Dict, Any


def easter(year: int) -> date:
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


def get_hamburg_holidays(year: int) -> List[Tuple[date, str]]:
    """Gibt alle Hamburger Feiertage für ein Jahr zurück."""
    e = easter(year)
    holidays: List[Tuple[date, str]] = [
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


SONDERTAG_FARBEN: Dict[str, Dict[str, str]] = {
    "Urlaub":                  {"bg": "#FFCC00", "text": "#3E2000"},  # Excel: Goldgelb
    "Krank":                   {"bg": "#FF0000", "text": "#FFFFFF"},  # Excel: Knallrot
    "Krank wegen Kind":        {"bg": "#FF0000", "text": "#FFFFFF"},  # Excel: gleich wie Krank
    "Schule":                  {"bg": "#92D050", "text": "#1B5E20"},
    "Innung":                  {"bg": "#00B0F0", "text": "#0D47A1"},
    "Prüfung Gesel. Teil 1/2": {"bg": "#E6B9B8", "text": "#4E342E"},  # Excel: Rosa (nicht Blau)
    "Schulung Firma":          {"bg": "#8EB4E3", "text": "#0D47A1"},  # Excel: mittleres Blau
    "Überstd.":                {"bg": "#7030A0", "text": "#FFFFFF"},
    "KUG":                     {"bg": "#FAC090", "text": "#4E342E"},
    "Q":                       {"bg": "#9BBB59", "text": "#1B5E20"},
    "Mutterschutz":            {"bg": "#FF0066", "text": "#FFFFFF"},
    "P":                       {"bg": "#00B0F0", "text": "#0D47A1"},
    "Feiertag":                {"bg": "#B0BEC5", "text": "#263238"},
    "MA Gespräch":             {"bg": "#B2DFDB", "text": "#004D40"},
    "Schulung":                {"bg": "#C8E6C9", "text": "#2E7D32"},
    "Berufschule":             {"bg": "#90CAF9", "text": "#0D47A1"},
}

GRUPPEN_REIHENFOLGE: List[str] = ["KD", "ST", "P1", "P2", "KDF", "MT", "Büro"]

GRUPPEN_FARBEN: Dict[str, str] = {
    "KD":   "#1565C0",
    "ST":   "#2E7D32",
    "KDF":  "#6A1B9A",
    "MT":   "#E65100",
    "P1":   "#00695C",
    "P2":   "#558B2F",
    "Büro": "#4E342E",
}
