"""Lectura CSV sin inferir tipos: preserva ceros iniciales y fila original."""

import csv
import io
from hashlib import sha256
from pathlib import Path
from src.extractors.base import BaseExtractor


class CSVExtractor(BaseExtractor):
    def __init__(self, path, required_columns=(), **options):
        super().__init__(path=str(path), **options)
        self.path = Path(path)
        self.required_columns = set(required_columns)

    def extract(self):
        # La huella corresponde al mismo contenido que se analiza.
        payload = self.path.read_bytes()
        self.digest = sha256(payload).hexdigest()
        with io.StringIO(payload.decode("utf-8-sig"), newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
                raise ValueError(f"Columnas duplicadas en {self.path}")
            if not self.required_columns.issubset(reader.fieldnames or []):
                missing = self.required_columns - set(reader.fieldnames or [])
                raise ValueError(f"Columnas faltantes en {self.path}: {missing}")
            try:
                for row in reader:
                    if None in row or any(v is None for v in row.values()):
                        raise ValueError(f"CSV mal formado, línea {reader.line_num}")
                    yield {**row, "_line": reader.line_num, "_raw": dict(row)}
            except csv.Error as exc:
                raise ValueError(
                    f"CSV mal formado en {self.path}, línea {reader.line_num}: {exc}"
                ) from exc

    def metadata(self):
        return {**super().metadata(), "sha256": self.digest}
