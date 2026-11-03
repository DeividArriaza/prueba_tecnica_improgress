"""Flujo de carga única: centros de votación y resultados históricos.
[TEMPLATE — completar]
"""
from __future__ import annotations

from src.pipelines.base_pipeline import Pipeline


def build_centros_pipeline() -> Pipeline:
    """TODO: armar extractor + transformers + validaciones + FullLoader."""
    raise NotImplementedError("TODO: implementar")


def build_resultados_pipeline() -> Pipeline:
    """TODO: armar extractor + transformers + validaciones + FullLoader.

    Considerar que las mesas deben quedar registradas en
    electoral.mesas_votacion (no viene un archivo de mesas: hay que derivarlas).
    """
    raise NotImplementedError("TODO: implementar")
