"""Pruebas de las transformaciones.  [TEMPLATE — completar]

Se espera al menos una prueba real por cada transformación implementada.
Las transformaciones son funciones sobre datos: probarlas no requiere base
de datos.
"""
from src.transformers.common import TrimStrings


def test_trim_strings():
    records = [{"nombre": "  Sololá  ", "codigo": "07"}]
    out = list(TrimStrings().transform(records))
    assert out[0]["nombre"] == "Sololá"


def test_normalize_text():
    # TODO: implementar cuando NormalizeText esté listo
    pass


def test_cast_numeric_con_separador_de_miles():
    # TODO: "1,234" debe convertirse a 1234
    pass


def test_parse_dates_formato_mixto():
    # TODO: "05/03/2019" y "2019-03-05" deben dar la misma fecha
    pass
