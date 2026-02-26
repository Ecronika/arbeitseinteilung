from app.helpers import get_hamburg_holidays

def test_hamburg_holidays():
    holidays = get_hamburg_holidays(2024)
    names = [h[1] for h in holidays]
    assert "Neujahr" in names
    assert "Heiligabend" in names
