"""Loaders de PostgreSQL.  [TEMPLATE — completar]"""
from __future__ import annotations

from typing import Iterable

from src.loaders.base import BaseLoader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FullLoader(BaseLoader):
    """Carga completa de data histórica.

    REQUISITO: debe ser idempotente. Ejecutarla dos veces no debe duplicar
    información ni dejar la tabla en un estado inconsistente.

    TODO: decidir la estrategia (¿control por hash de archivo? ¿tabla de
    control? ¿ON CONFLICT? ¿carga a staging + swap?) y justificarla.
    Ojo: el modelo actual no tiene restricciones de unicidad — eso también
    es parte de lo que debes analizar en MEJORAS_MODELO.md.
    """

    def load(self, records: Iterable[dict]) -> int:
        raise NotImplementedError("TODO: implementar")


class IncrementalLoader(BaseLoader):
    """Actualización diaria del padrón.

    Debe manejar los tres casos:
      - altas: registros que no existían
      - cambios: registros existentes con datos distintos (p. ej. traslado)
      - bajas: registros que pasan a estado suspendido / fallecido

    TODO: implementar upsert, registrar la marca de agua (watermark) del día
    procesado y permitir reprocesar una fecha específica sin duplicar.
    """

    def load(self, records: Iterable[dict]) -> int:
        raise NotImplementedError("TODO: implementar")
