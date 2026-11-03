"""Transformaciones puras; los errores de celda viajan hacia cuarentena."""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata
from src.transformers.base import BaseTransformer


def canonical(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(c for c in text if not unicodedata.combining(c)).upper().split()
    )


def error(row, reason):
    row.setdefault("_errors", []).append(reason)


class TrimStrings(BaseTransformer):
    def transform(self, records):
        for row in records:
            yield {
                k: (v.strip() or None) if isinstance(v, str) else v
                for k, v in row.items()
            }


class NormalizeText(BaseTransformer):
    def __init__(self, fields):
        self.fields = fields

    def transform(self, records):
        for source in records:
            row = dict(source)
            for field in self.fields:
                if row.get(field) is not None:
                    row[field] = canonical(row[field])
            yield row


class CastNumeric(BaseTransformer):
    """El formato depende de la columna, no de adivinar el valor."""

    def __init__(self, fields, decimal_fields=()):
        self.fields = fields
        self.decimal_fields = set(decimal_fields)

    def transform(self, records):
        for source in records:
            row = dict(source)
            for field in self.fields:
                value = row.get(field)
                if value is None:
                    continue
                try:
                    text = str(value).strip()
                    if field in self.decimal_fields:
                        if not re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", text):
                            raise ValueError()
                        number = Decimal(text.replace(",", "."))
                        row[field] = format(number, "f")
                    else:
                        if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)", text):
                            raise ValueError()
                        row[field] = int(text.replace(",", ""))
                except (ValueError, InvalidOperation):
                    error(row, f"numero_invalido:{field}")
            yield row


class ParseDates(BaseTransformer):
    def __init__(self, fields):
        self.fields = fields

    def transform(self, records):
        for source in records:
            row = dict(source)
            for field in self.fields:
                if row.get(field) is None:
                    continue
                for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        row[field] = (
                            datetime.strptime(str(row[field]), fmt).date().isoformat()
                        )
                        break
                    except ValueError:
                        pass
                else:
                    error(row, f"fecha_invalida:{field}")
            yield row


class StandardizeCategories(BaseTransformer):
    def __init__(self, mapping):
        self.mapping = {
            f: {canonical(k): v for k, v in m.items()} for f, m in mapping.items()
        }

    def transform(self, records):
        for source in records:
            row = dict(source)
            for field, mapping in self.mapping.items():
                if row.get(field) is not None:
                    value = canonical(row[field])
                    row[field] = mapping.get(value, value)
            yield row


class Deduplicate(BaseTransformer):
    """No elige un ganador arbitrario cuando hay informaci?n contradictoria."""

    def __init__(self, key):
        self.key = key

    def transform(self, records):
        groups = defaultdict(list)
        for row in records:
            groups[tuple(row.get(k) for k in self.key)].append(row)
        for rows in groups.values():

            def business(row):
                return {k: v for k, v in row.items() if not k.startswith("_")}

            conflict = any(business(row) != business(rows[0]) for row in rows[1:])
            for i, source in enumerate(rows):
                row = dict(source)
                if conflict:
                    error(row, "duplicado_conflictivo")
                elif i:
                    row["_duplicate"] = True
                yield row
