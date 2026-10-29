import json
import threading

from honest_catalog import budget as budget_mod
from honest_catalog.beam import BeamClient, BeamUnavailable
from honest_catalog.budget import DailyBudget


def test_cap_blocks_after_limit(tmp_path):
    b = DailyBudget(tmp_path / "u.json", cap=3)
    assert [b.try_spend() for _ in range(4)] == [True, True, True, False]
    assert b.used() == 3 and b.remaining() == 0


def test_count_survives_restart_and_resets_next_day(tmp_path):
    day = {"v": "2026-11-01"}
    path = tmp_path / "u.json"
    DailyBudget(path, cap=5, today=lambda: day["v"]).try_spend(2)
    assert DailyBudget(path, cap=5, today=lambda: day["v"]).used() == 2
    day["v"] = "2026-11-02"
    b = DailyBudget(path, cap=5, today=lambda: day["v"])
    assert b.used() == 0 and b.remaining() == 5
    assert json.loads(path.read_text()) == {"date": "2026-11-01", "calls": 2}


def test_multi_call_reservation_is_all_or_nothing(tmp_path):
    b = DailyBudget(tmp_path / "u.json", cap=4)
    assert b.try_spend(3)
    assert not b.try_spend(2)
    assert b.used() == 3


def test_corrupt_file_counts_as_zero(tmp_path):
    path = tmp_path / "u.json"
    path.write_text("{not json")
    assert DailyBudget(path, cap=2).remaining() == 2


def test_concurrent_spending_never_passes_cap(tmp_path):
    b = DailyBudget(tmp_path / "u.json", cap=25)
    results = []
    threads = [threading.Thread(target=lambda: results.append(b.try_spend())) for _ in range(60)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert results.count(True) == 25 and b.used() == 25


def test_default_cap_is_40(monkeypatch):
    monkeypatch.delenv("BEAM_DAILY_CALL_CAP", raising=False)
    assert budget_mod.daily_cap_from_env() == 40
    monkeypatch.setenv("BEAM_DAILY_CALL_CAP", "7")
    assert budget_mod.daily_cap_from_env() == 7
    monkeypatch.setenv("BEAM_DAILY_CALL_CAP", "lots")
    assert budget_mod.daily_cap_from_env() == 40


def test_client_refuses_without_token_or_budget(tmp_path):
    b = DailyBudget(tmp_path / "u.json", cap=0)
    assert BeamClient(budget=b, token="").status() == (False, "no_token")
    assert BeamClient(budget=b, token="x").status() == (False, "cap_reached")
    try:
        BeamClient(budget=b, token="x").chat("s", "u")
    except BeamUnavailable as exc:
        assert str(exc) == "cap_reached"
    else:
        raise AssertionError("expected BeamUnavailable")
