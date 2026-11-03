"""Conexión transaccional: confirma al terminar y revierte ante cualquier fallo."""

from __future__ import annotations

from contextlib import contextmanager

import psycopg2

from src.config.settings import DBSettings


@contextmanager
def get_connection():
    s = DBSettings.from_env()
    conn = psycopg2.connect(
        host=s.host,
        port=s.port,
        dbname=s.database,
        user=s.user,
        password=s.password,
        connect_timeout=10,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
