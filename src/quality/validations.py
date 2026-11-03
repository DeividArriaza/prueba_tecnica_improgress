"""Resultado y validador genérico. Las reglas electorales están en business.py.

Un registro que no pasa una validación NO debe romper la ejecución en
silencio. Decide qué haces con él (cuarentena, descarte con log, o fallo
del flujo) y documenta el criterio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable


@dataclass
class ValidationResult:
    valid: list[dict] = field(default_factory=list)
    rejected: list[tuple[dict, str]] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        return {"validos": len(self.valid), "rechazados": len(self.rejected)}


class Validator:
    """Aplica una lista de reglas y separa válidos de rechazados."""

    def __init__(self, rules: list[tuple[str, Callable[[dict], bool]]]) -> None:
        self.rules = rules

    def run(self, records: Iterable[dict]) -> ValidationResult:
        result = ValidationResult()
        for r in records:
            for name, rule in self.rules:
                if not rule(r):
                    result.rejected.append((r, name))
                    break
            else:
                result.valid.append(r)
        return result


# ---------------------------------------------------------------------------
# Reglas mínimas esperadas (implementar):
#   1. llave natural no nula
#   2. votos no negativos
#   3. total_votantes_mesa <= total_empadronados_mesa
#   4. codigo_centro_votacion existe en el catálogo de centros
#   5. estado_registro dentro del dominio permitido
#   6. fechas parseables y dentro de un rango razonable
# ---------------------------------------------------------------------------
