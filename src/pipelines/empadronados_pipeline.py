"""Flujo incremental: padrón electoral (fuente viva).  [TEMPLATE — completar]"""
from __future__ import annotations

from src.pipelines.base_pipeline import Pipeline


def build_empadronados_pipeline(fecha: str) -> Pipeline:
    """Construye el flujo para una fecha de proceso.

    Args:
        fecha: fecha de corte en formato YYYY-MM-DD (permite backfill).

    TODO: armar extractor + transformers + validaciones + IncrementalLoader.
    """
    raise NotImplementedError("TODO: implementar")
