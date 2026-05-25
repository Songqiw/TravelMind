from tools.check_ticket_availability import check_ticket_availability


def test_check_ticket_availability_returns_allowed_status(monkeypatch):
    captured_options = None

    def fake_choice(options):
        nonlocal captured_options
        captured_options = options
        return "available"

    monkeypatch.setattr("tools.check_ticket_availability.random.choice", fake_choice)

    result = check_ticket_availability("故宫", "2026-06-01")

    assert result == "available"
    assert captured_options == ["available", "sold_out"]
