"""Nunca ejecuta el DDL destructivo contra la base de trabajo."""

import os
from pathlib import Path
from uuid import uuid4
import psycopg2
from psycopg2 import sql
import pytest
from src.config.settings import DBSettings
from src.utils.db import get_connection
from src.pipelines.factory import build_pipeline
from src.loaders.postgres_loader import watermark

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="Definir RUN_DB_TESTS=1 para PostgreSQL",
    ),
]


@pytest.fixture
def database(monkeypatch):
    settings = DBSettings.from_env()
    admin = psycopg2.connect(
        host=settings.host,
        port=settings.port,
        dbname="postgres",
        user=settings.user,
        password=settings.password,
    )
    admin.autocommit = True
    name = "etl_test_" + uuid4().hex
    with admin.cursor() as cur:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    monkeypatch.setenv("POSTGRES_DB", name)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    Path("sql/01_ddl_electoral.sql").read_text(encoding="utf-8")
                )
        yield
    finally:
        with admin.cursor() as cur:
            cur.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )
        admin.close()


def test_historical_idempotency_and_daily_updates(database):
    for name in ("centros_votacion", "resultados_historicos"):
        first = build_pipeline(name).run()
        second = build_pipeline(name).run()
        assert first["insertadas"] > 0 and second["cargadas"] == 0
    counts = []
    original_created = None
    for day in (2, 3, 4):
        metrics = build_pipeline("empadronados", f"2026-03-0{day}").run()
        counts.append(metrics)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT codigo_mesa,estado_registro,created_at FROM electoral.empadronados WHERE id_empadronado='E0001026'"
                )
                mesa, state, created = cur.fetchone()
                assert mesa == ("1202001-14" if day == 2 else "1701005-07")
                if day == 2:
                    original_created = created
                else:
                    assert created == original_created
                cur.execute(
                    "SELECT estado_registro FROM electoral.empadronados WHERE id_empadronado='E0005122'"
                )
                assert cur.fetchone()[0] == ("activo" if day == 2 else "fallecido")
    assert counts[1]["insertadas"] > 0 and counts[1]["actualizadas"] > 0
    repeat = build_pipeline("empadronados", "2026-03-04").run()
    assert repeat["cargadas"] == 0
    with get_connection() as conn:
        assert watermark(conn) == "2026-03-04"
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM electoral.empadronados")
            # 17.898 válidas del último archivo + 34 últimas versiones válidas
            # de personas rechazadas en ese corte. No borrar por ausencia/rechazo.
            assert cur.fetchone()[0] == 17932
            cur.execute(
                "SELECT count(*) FROM electoral.empadronados WHERE estado_registro IN ('suspendido','fallecido')"
            )
            assert cur.fetchone()[0] > 0
    with pytest.raises(ValueError, match="anterior al watermark"):
        build_pipeline("empadronados", "2026-03-02").run()


def test_failure_rolls_back_data_and_watermark(database, monkeypatch):
    build_pipeline("centros_votacion").run()
    pipeline = build_pipeline("empadronados", "2026-03-02")
    original = pipeline.loader.load

    def failing(records, conn=None):
        original(records, conn=conn)
        raise RuntimeError("fallo simulado después de escribir")

    monkeypatch.setattr(pipeline.loader, "load", failing)
    with pytest.raises(RuntimeError):
        pipeline.run()
    with get_connection() as conn:
        assert watermark(conn) is None
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM electoral.empadronados")
            assert cur.fetchone()[0] == 0


def test_rebuild_is_atomic_and_preserves_current_cutoff(
    database, monkeypatch, tmp_path
):
    import shutil
    import yaml
    from src.config import settings
    from src.config.sources import snapshot_files
    from src.pipelines.rebuild_pipeline import rebuild_padron

    build_pipeline("centros_votacion").run()
    for day in (2, 3, 4):
        build_pipeline("empadronados", f"2026-03-0{day}").run()
    cfg = settings.load_config()
    for value, path in snapshot_files():
        shutil.copyfile(path, tmp_path / path.name)
    cfg["sources"]["empadronados"]["path_pattern"] = str(
        tmp_path / "empadronados_{fecha}.csv"
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    monkeypatch.setattr(settings, "CONFIG_PATH", config_path)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM electoral.empadronados ORDER BY id_empadronado")
            before = cur.fetchall()
    summary = rebuild_padron("2026-03-04")
    assert summary["publicadas"] == 17932 and summary["cargadas"] == 0
    with get_connection() as conn:
        assert watermark(conn) == "2026-03-04"
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM electoral.empadronados ORDER BY id_empadronado")
            assert cur.fetchall() == before
            cur.execute("SELECT count(*) FROM electoral.carga_log")
            logs = cur.fetchone()[0]
    (tmp_path / "empadronados_20260303.csv").write_text("malformed", encoding="utf-8")
    with pytest.raises(ValueError):
        rebuild_padron("2026-03-04")
    with get_connection() as conn:
        assert watermark(conn) == "2026-03-04"
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM electoral.empadronados ORDER BY id_empadronado")
            assert cur.fetchall() == before
            cur.execute("SELECT count(*) FROM electoral.carga_log")
            assert cur.fetchone()[0] == logs
    with pytest.raises(ValueError, match="debe llegar"):
        rebuild_padron("2026-03-02")
