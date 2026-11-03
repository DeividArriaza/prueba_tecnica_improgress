"""Contrato de carga.

Dos modos que la prueba pide distinguir explícitamente:
  - FullLoader        -> data histórica, se carga una sola vez, idempotente
  - IncrementalLoader -> padrón, actualización diaria (altas, cambios, bajas)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class BaseLoader(ABC):
    """El contexto de escritura pertenece al store y se comparte con la auditoría."""

    def __init__(self) -> None:
        self.metrics: dict[str, int] = {}

    @abstractmethod
    def load(self, records: Iterable[dict], *, conn=None) -> int:
        """Devuelve afectadas y publica insertadas/actualizadas/sin_cambios en metrics."""
        raise NotImplementedError
