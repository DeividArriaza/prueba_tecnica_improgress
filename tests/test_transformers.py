from copy import deepcopy
from src.transformers.common import (
    TrimStrings,
    NormalizeText,
    CastNumeric,
    ParseDates,
    StandardizeCategories,
    Deduplicate,
)
from src.transformers.base import TransformerPipeline


def test_clean_text_preserves_codes_and_input():
    original = [{"nombre": "  Sololá   CENTRO ", "codigo": "07"}]
    before = deepcopy(original)
    out = list(
        TransformerPipeline(TrimStrings(), NormalizeText(["nombre"])).transform(
            original
        )
    )
    assert out == [{"nombre": "SOLOLA CENTRO", "codigo": "07"}]
    assert original == before


def test_numeric_formats_are_column_specific():
    out = list(
        CastNumeric(["votos", "latitud"], ["latitud"]).transform(
            [{"votos": "1,234", "latitud": "14,625"}]
        )
    )
    assert out == [{"votos": 1234, "latitud": "14.625"}]


def test_invalid_number_is_rejected_without_becoming_zero():
    row = list(CastNumeric(["votos"]).transform([{"votos": "1,2"}]))[0]
    assert row["votos"] == "1,2"
    assert row["_errors"] == ["numero_invalido:votos"]


def test_dates_mix_and_invalid_date():
    rows = list(
        ParseDates(["fecha"]).transform(
            [{"fecha": "05/03/2019"}, {"fecha": "2019-03-05"}, {"fecha": "31/02/2020"}]
        )
    )
    assert rows[0]["fecha"] == rows[1]["fecha"] == "2019-03-05"
    assert rows[2]["_errors"] == ["fecha_invalida:fecha"]


def test_categories_are_explicit_and_unknowns_preserved():
    rows = list(
        StandardizeCategories({"sexo": {"femenino": "F"}}).transform(
            [{"sexo": "FEMENINO"}, {"sexo": "desconocido"}]
        )
    )
    assert rows[0]["sexo"] == "F"
    assert rows[1]["sexo"] == "DESCONOCIDO"


def test_duplicates_ignore_line_metadata_but_reject_conflicting_group():
    records = [
        {"id": "a", "value": 1, "_line": 2},
        {"id": "a", "value": 1, "_line": 3},
        {"id": "b", "value": 1},
        {"id": "b", "value": 2},
    ]
    rows = list(Deduplicate(["id"]).transform(records))
    assert rows[1]["_duplicate"]
    assert all("duplicado_conflictivo" in r["_errors"] for r in rows[2:])
