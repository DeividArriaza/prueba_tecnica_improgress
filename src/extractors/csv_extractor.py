"""Extractor de archivos CSV.  [TEMPLATE — completar]"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from src.extractors.base import BaseExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CSVExtractor(BaseExtractor):
    def __init__(self, path: str | Path, **options) -> None:
        super().__init__(path=str(path), **options)
        self.path = Path(path)

    def extract(self) -> Iterable[dict]:
        # TODO (candidato):
        #  - manejar archivo inexistente de forma explícita
        #  - decidir si lees en streaming o en memoria y por qué
        #  - normalizar los nombres de columna si hace falta
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        logger.info("Leyendo %s", self.path)
        with open(self.path, newline="", encoding="utf-8") as fh:
            yield from csv.DictReader(fh)
