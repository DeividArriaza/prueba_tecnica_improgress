"""Transformaciones reutilizables.  [TEMPLATE — completar]

Estas son las piezas donde se concentra el trabajo real de la prueba.
Los datos de origen traen inconsistencias reales: acentos, mayúsculas,
espacios, decimales con coma, separadores de miles, fechas en dos formatos,
valores categóricos no estandarizados, duplicados y llaves huérfanas.
"""
from __future__ import annotations

from typing import Iterable

from src.transformers.base import BaseTransformer


class TrimStrings(BaseTransformer):
    """Ejemplo de referencia ya implementado: recorta espacios."""

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        for r in records:
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}


class NormalizeText(BaseTransformer):
    """Estandariza nombres de departamento / municipio / centro.

    TODO: decidir la forma canónica (¿se conservan acentos? ¿title case?) y
    aplicarla de forma consistente en todas las fuentes.
    """

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        raise NotImplementedError("TODO: implementar")


class CastNumeric(BaseTransformer):
    """Convierte columnas numéricas que vienen como texto.

    TODO: manejar vacíos, negativos, separadores de miles y coma decimal.
    """

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        raise NotImplementedError("TODO: implementar")


class ParseDates(BaseTransformer):
    """Convierte fechas en formato mixto (YYYY-MM-DD y DD/MM/YYYY)."""

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        raise NotImplementedError("TODO: implementar")


class StandardizeCategories(BaseTransformer):
    """Estandariza valores categóricos: area, sexo, estado_registro, partido."""

    def __init__(self, mapping: dict[str, dict[str, str]]) -> None:
        self.mapping = mapping

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        raise NotImplementedError("TODO: implementar")


class Deduplicate(BaseTransformer):
    """Elimina duplicados según la llave natural.

    TODO: definir el criterio de sobrevivencia cuando dos filas comparten la
    llave pero difieren en el resto de columnas. Documentarlo.
    """

    def __init__(self, key: list[str]) -> None:
        self.key = key

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        raise NotImplementedError("TODO: implementar")
