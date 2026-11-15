import re
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.analytics import Period
from dashboard.snapshots import ReportSnapshot, Source


def test_demo_page_runs_without_credentials_and_locks_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHBOARD_DATA_SOURCE", "demo")
    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "dashboard/app.py", default_timeout=15
    ).run()
    assert not app.exception
    assert "Datos sintéticos de demostración" in "".join(x.value for x in app.markdown)
    selector = next(x for x in app.selectbox if x.label == "Fuente de datos")
    assert selector.options == ["Demo"] and selector.disabled
    assert any(x.label == "Aplicar" for x in app.button)
    export = app.get("popover")[0]
    assert any("Habilitar edición" in x.value for x in export.get("markdown"))
    assert sum("Habilitar edición" in x.value for x in app.markdown) == 1
    assert re.search(
        r"\d{1,2} [a-z]{3} al \d{1,2} [a-z]{3}",
        " ".join(x.value for x in app.markdown if 'class="tl-help"' in x.value),
    )


def test_cache_excludes_secret_arguments_and_never_logs_them(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from dashboard import loading
    from dashboard.snapshots import load_report

    calls = []

    def fake(source: Source, period: Period, **kwargs: Any) -> ReportSnapshot:
        calls.append(1)
        return load_report("demo", period, today=kwargs["today"])

    monkeypatch.setattr(loading, "load_report", fake)
    script = """
import streamlit as st
from datetime import date
from dashboard.analytics import Period
from dashboard.loading import cached_report
p=Period(date(2026,4,17),date(2026,4,30))
cached_report('demo',p,date(2026,4,30),'',_api_key='synthetic-key-a')
cached_report('demo',p,date(2026,4,30),'',_api_key='synthetic-key-b')
st.write('done')
"""
    app = AppTest.from_string(script, default_timeout=15).run()
    assert not app.exception
    assert len(calls) == 1
    assert "synthetic-key-a" not in caplog.text and "synthetic-key-b" not in caplog.text


def test_filters_only_publish_after_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHBOARD_DATA_SOURCE", "demo")
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "dashboard/app.py", default_timeout=15
    ).run()
    app.selectbox(key="tl-preset").select("7 días").run()
    assert any(
        "14 días" in x.value for x in app.markdown if 'class="tl-help"' in x.value
    )
    next(x for x in app.button if x.label == "Aplicar").click().run()
    assert not app.exception
    assert any(
        "7 días" in x.value for x in app.markdown if 'class="tl-help"' in x.value
    )
    app.selectbox(key="tl-preset").select("Personalizado").run()
    assert len(app.date_input) == 1
    assert any(
        "7 días" in x.value for x in app.markdown if 'class="tl-help"' in x.value
    )


def test_environment_can_lock_an_existing_api_selection_to_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dashboard import loading
    from dashboard.snapshots import load_report

    def fake(source: Source, period: Period, **kwargs: Any) -> ReportSnapshot:
        return load_report("demo", period, today=kwargs["today"])

    monkeypatch.setattr(loading, "load_report", fake)
    monkeypatch.setenv("DASHBOARD_DATA_SOURCE", "api")
    monkeypatch.setenv("API_BASE_URL", "http://test")
    monkeypatch.setenv("API_KEY", "synthetic")
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "dashboard/app.py", default_timeout=15
    ).run()
    assert app.selectbox(key="tl-source").value == "api"
    monkeypatch.setenv("DASHBOARD_DATA_SOURCE", "demo")
    app.run()
    assert not app.exception
    assert app.selectbox(key="tl-source").options == ["Demo"]
    assert app.selectbox(key="tl-source").disabled
    assert app.session_state["_tl_filters"][0] == "demo"


def test_credential_change_invalidates_session_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dashboard import loading
    from dashboard.snapshots import load_report

    calls = []

    def fake(source: Source, period: Period, **kwargs: Any) -> ReportSnapshot:
        calls.append(kwargs["api_key"])
        return load_report("demo", period, today=kwargs["today"])

    monkeypatch.setattr(loading, "load_report", fake)
    app = AppTest.from_string(
        """
import streamlit as st
from datetime import date
from dashboard.analytics import Period
from dashboard.loading import load_cached_report
from dashboard.snapshots import SourceConfig
key='synthetic-b' if st.button('Rotate') else 'synthetic-a'
config=SourceConfig(('api','demo'),'api',False,'http://test',key)
p=Period(date(2026,4,17),date(2026,4,30))
load_cached_report('api',p,today=date(2026,4,30),config=config)
""",
        default_timeout=15,
    ).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert calls == ["synthetic-a", "synthetic-b"]
