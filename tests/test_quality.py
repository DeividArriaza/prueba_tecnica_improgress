from datetime import date
import pytest
from src.pipelines.factory import build_pipeline
from src.quality.business import BusinessValidator
from src.pipelines.factory import ElectionDefaults


@pytest.mark.parametrize("fecha", ["20260304", "2026-02-30"])
def test_pipeline_rejects_invalid_or_noncanonical_cutoff(fecha):
    with pytest.raises(ValueError):
        build_pipeline("empadronados", fecha)


def validator(source="empadronados"):
    return BusinessValidator(
        source,
        (
            ["id_empadronado"]
            if source == "empadronados"
            else ["anio_eleccion", "tipo_eleccion", "vuelta", "codigo_mesa", "partido"]
        ),
        {"001": {"codigo_departamento": "01", "codigo_municipio": "0101"}},
        date(2026, 3, 4),
    )


def person(**kwargs):
    return dict(
        id_empadronado="E1",
        codigo_centro_votacion="001",
        codigo_mesa="001-01",
        sexo=None,
        rango_edad="18-25",
        estado_registro="activo",
        fecha_inscripcion="2020-01-01",
        fecha_ultima_actualizacion="2026-03-03",
        **kwargs
    )


def test_required_key_and_unknown_center():
    row = person()
    row.update(id_empadronado=None, codigo_centro_votacion="999")
    reasons = validator().reasons(row)
    assert "llave_natural_vacia" in reasons and "centro_inexistente" in reasons


def test_future_dates_and_status_invalid():
    row = person()
    row.update(fecha_ultima_actualizacion="2026-03-05", estado_registro="eliminado")
    reasons = validator().reasons(row)
    assert "estado_invalido" in reasons
    assert "fecha_fuera_rango:fecha_ultima_actualizacion" in reasons


def results():
    base = dict(
        anio_eleccion=2023,
        tipo_eleccion="presidencial",
        vuelta=1,
        codigo_centro_votacion="001",
        codigo_mesa="001-01",
        codigo_departamento="01",
        codigo_municipio="0101",
        votos_nulos=2,
        votos_en_blanco=1,
        total_empadronados_mesa=100,
        total_votantes_mesa=80,
    )
    return [
        dict(base, partido="A", votos_validos=40),
        dict(base, partido="B", votos_validos=37),
    ]


def test_negative_votes_quarantine_entire_table_group():
    rows = results()
    rows[0]["votos_validos"] = -1
    out = validator("resultados_historicos").run(rows)
    assert not out.valid and len(out.rejected) == 2


def test_sum_warning_does_not_invent_votes():
    rows = results()
    rows[0]["votos_validos"] = 39
    out = validator("resultados_historicos").run(rows)
    assert len(out.valid) == 2 and out.valid[0]["votos_validos"] == 39
    assert out.valid[0]["_warnings"] == ["suma_votos_no_coincide"]


def test_empty_round_is_only_defaulted_for_single_round_elections():
    rows = list(
        ElectionDefaults().transform(
            [
                {"tipo_eleccion": "legislativa", "vuelta": None},
                {"tipo_eleccion": "presidencial", "vuelta": None},
            ]
        )
    )
    assert rows[0]["vuelta"] == "1" and rows[1]["vuelta"] is None
