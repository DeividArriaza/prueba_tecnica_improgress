"""Reglas de fila y de mesa; no inventa datos electorales."""

from collections import defaultdict
from datetime import date
import re
from src.quality.validations import ValidationResult

VOTES = (
    "votos_validos",
    "votos_nulos",
    "votos_en_blanco",
    "total_empadronados_mesa",
    "total_votantes_mesa",
)
GROUP = ("anio_eleccion", "tipo_eleccion", "vuelta", "codigo_mesa")


class BusinessValidator:
    def __init__(self, source, key, catalog, cutoff):
        self.source, self.key = source, key
        self.catalog, self.cutoff = catalog, cutoff

    def reasons(self, row):
        reasons = list(row.get("_errors", []))
        if any(row.get(k) is None for k in self.key):
            reasons.append("llave_natural_vacia")
        for k, value in row.items():
            limit = (
                255
                if k.startswith("nombre_") or k in ("direccion", "partido", "candidato")
                else 50
            )
            if not k.startswith("_") and value is not None and len(str(value)) > limit:
                reasons.append(f"longitud_excedida:{k}")
        if self.source == "centros_votacion":
            for field in ("cantidad_mesas", "capacidad_maxima"):
                if row.get(field) is not None and (
                    not isinstance(row[field], int) or row[field] < 0
                ):
                    reasons.append(f"cantidad_invalida:{field}")
            for field, low, high in [("latitud", -90, 90), ("longitud", -180, 180)]:
                if row.get(field) is not None:
                    try:
                        if not low <= float(row[field]) <= high:
                            reasons.append(f"coordenada_fuera_rango:{field}")
                    except ValueError:
                        reasons.append(f"coordenada_invalida:{field}")
            if row.get("area") not in (None, "urbana", "rural"):
                reasons.append("area_invalida")
            year = row.get("anio_vigencia")
            if not isinstance(year, int) or not 1900 <= year <= self.cutoff.year:
                reasons.append("anio_invalido")
        elif self.source in ("resultados_historicos", "empadronados"):
            center = self.catalog.get(row.get("codigo_centro_votacion"))
            if center is None:
                reasons.append("centro_inexistente")
            mesa = row.get("codigo_mesa") or ""
            prefix = str(row.get("codigo_centro_votacion") or "") + "-"
            suffix = mesa[len(prefix) :] if mesa.startswith(prefix) else ""
            if not re.fullmatch(r"[0-9]+", suffix) or int(suffix) < 1:
                reasons.append("mesa_incompatible_con_centro")
        if self.source == "resultados_historicos":
            if any(not isinstance(row.get(f), int) or row[f] < 0 for f in VOTES):
                reasons.append("votos_invalidos_o_negativos")
            elif row["total_votantes_mesa"] > row["total_empadronados_mesa"]:
                reasons.append("votantes_superan_empadronados")
            elif (
                row["votos_validos"] > row["total_votantes_mesa"]
                or row["votos_nulos"] + row["votos_en_blanco"]
                > row["total_votantes_mesa"]
            ):
                reasons.append("votos_superan_total_votantes")
            if row.get("tipo_eleccion") not in (
                "presidencial",
                "legislativa",
                "municipal",
            ):
                reasons.append("tipo_eleccion_invalido")
            if row.get("vuelta") not in (1, 2):
                reasons.append("vuelta_invalida")
            if (
                not isinstance(row.get("anio_eleccion"), int)
                or not 1900 <= row["anio_eleccion"] <= self.cutoff.year
            ):
                reasons.append("anio_invalido")
            if center and any(
                row.get(k) != center.get(k)
                for k in ("codigo_departamento", "codigo_municipio")
            ):
                reasons.append("geografia_no_coincide_con_catalogo")
        if self.source == "empadronados":
            if row.get("estado_registro") not in ("activo", "suspendido", "fallecido"):
                reasons.append("estado_invalido")
            if row.get("sexo") not in (None, "M", "F"):
                reasons.append("sexo_invalido")
            if row.get("rango_edad") not in ("18-25", "26-35", "36-45", "46-60", "61+"):
                reasons.append("rango_edad_invalido")
            parsed = []
            for field in ("fecha_inscripcion", "fecha_ultima_actualizacion"):
                try:
                    value = date.fromisoformat(row.get(field) or "")
                    if not date(1900, 1, 1) <= value <= self.cutoff:
                        reasons.append(f"fecha_fuera_rango:{field}")
                    parsed.append(value)
                except ValueError:
                    reasons.append(f"fecha_invalida:{field}")
            if len(parsed) == 2 and parsed[0] > parsed[1]:
                reasons.append("inscripcion_posterior_actualizacion")
        return reasons

    def run(self, records):
        rows = list(records)
        reasons = {id(row): self.reasons(row) for row in rows}
        if self.source == "resultados_historicos":
            groups = defaultdict(list)
            for row in rows:
                groups[tuple(row.get(k) for k in GROUP)].append(row)
            for group in groups.values():
                reason = None
                if any(reasons[id(r)] for r in group):
                    reason = "mesa_con_registros_invalidos"
                else:
                    totals = {tuple(r[f] for f in VOTES[1:]) for r in group}
                    if len(totals) != 1:
                        reason = "totales_mesa_inconsistentes"
                    elif (
                        sum(r["votos_validos"] for r in group)
                        + group[0]["votos_nulos"]
                        + group[0]["votos_en_blanco"]
                        != group[0]["total_votantes_mesa"]
                    ):
                        for row in group:
                            row.setdefault("_warnings", []).append(
                                "suma_votos_no_coincide"
                            )
                if reason:
                    for row in group:
                        reasons[id(row)].append(reason)
        result = ValidationResult()
        for row in rows:
            if reasons[id(row)]:
                result.rejected.append((row, ";".join(sorted(set(reasons[id(row)])))))
            else:
                result.valid.append(row)
        return result
