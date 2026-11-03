"""Contrato de extracción.

Un extractor sabe LEER de una fuente y nada más: no transforma ni carga.
Agregar una fuente nueva (API, base de datos, parquet) debe ser crear una
subclase, no modificar el pipeline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class BaseExtractor(ABC):
    """Interfaz común de todas las fuentes."""

    def __init__(self, **options: Any) -> None:
        self.options = options

    @abstractmethod
    def extract(self) -> Iterable[dict]:
        """Devuelve los registros crudos de la fuente, sin transformar."""
        raise NotImplementedError

    def metadata(self) -> dict:
        """Información de la ejecución (origen, filas leídas, etc.)."""
        return {"extractor": type(self).__name__, "options": self.options}
