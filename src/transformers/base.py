"""Contrato de transformación.

Los transformers deben ser componibles: la salida de uno es la entrada del
siguiente. Deben ser funciones puras siempre que se pueda (facilita probarlos).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class BaseTransformer(ABC):
    @abstractmethod
    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        raise NotImplementedError


class TransformerPipeline(BaseTransformer):
    """Encadena varios transformers en orden."""

    def __init__(self, *transformers: BaseTransformer) -> None:
        self.transformers = transformers

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        for t in self.transformers:
            records = t.transform(records)
        return records
