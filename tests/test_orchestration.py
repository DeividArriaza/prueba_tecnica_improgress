from contextlib import contextmanager
from types import SimpleNamespace
import json
import pytest

pytest.importorskip("prefect")
import psycopg2
import orchestration.flows as flows


@pytest.mark.parametrize(
    "exception,expected",
    [(psycopg2.OperationalError("temporary"), True), (ValueError("bad data"), False)],
)
def test_retry_classification(exception, expected):
    class State:
        def result(self):
            raise exception

    assert flows.retry_transient(None, None, State()) is expected


def test_preparation_has_retries_and_is_called_before_loading(monkeypatch):
    assert flows.prepare_daily.retries == flows.SETTINGS["retries"]
    calls = []
    monkeypatch.setattr(flows, "prepare_daily", lambda: calls.append("prepare"))
    monkeypatch.setattr(flows, "daily_task", lambda value: calls.append(value))
    flows.daily_flow.fn("2026-03-04")
    assert calls == ["prepare", "2026-03-04"]


def test_pending_days_stop_on_first_failure(monkeypatch):
    monkeypatch.setattr(flows, "prepare_daily", lambda: "2026-03-01")
    monkeypatch.setattr(
        flows,
        "snapshot_files",
        lambda: [("2026-03-02", None), ("2026-03-03", None), ("2026-03-04", None)],
    )
    calls = []

    def task(value):
        calls.append(value)
        if value == "2026-03-03":
            raise ValueError("bad file")

    monkeypatch.setattr(flows, "daily_task", task)
    with pytest.raises(ValueError):
        flows.daily_flow.fn()
    assert calls == ["2026-03-02", "2026-03-03"]


def test_alert_payload_and_delivery_failure(monkeypatch, capsys):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.invalid/webhook")
    sent = []

    def request(value, timeout):
        sent.append((json.loads(value.data), timeout))
        raise OSError("unavailable")

    monkeypatch.setattr(flows, "urlopen", request)
    flows.alert(
        SimpleNamespace(name="test"),
        SimpleNamespace(id="run1"),
        SimpleNamespace(name="Failed", message="reason"),
    )
    assert sent[0][0]["state"] == "Failed" and sent[0][1] == 10
    assert "No se pudo entregar alerta" in capsys.readouterr().err
