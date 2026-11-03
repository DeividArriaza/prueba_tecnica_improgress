from contextlib import contextmanager
from datetime import date
import hashlib
import json
import pytest
import yaml
from src.extractors.base import BaseExtractor
from src.extractors.csv_extractor import CSVExtractor
from src.loaders.base import BaseLoader
from src.pipelines.base_pipeline import Pipeline
from src.quality.validations import ValidationResult
from src.config import settings
from src.config.sources import snapshot_files
from tests.test_quality import person, validator, results


@pytest.mark.parametrize(
    "text", ['codigo,nombre\n0101,"Sin cerrar', 'codigo,nombre\n0101,"A"extra\n']
)
def test_bad_quotes_are_structural_errors(tmp_path, text):
    path = tmp_path / "bad.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="CSV mal formado"):
        list(CSVExtractor(path, required_columns=["codigo", "nombre"]).extract())


def test_unicode_mesa_is_rejected_without_crashing():
    row = person()
    row["codigo_mesa"] = "001-\u00b2"
    assert "mesa_incompatible_con_centro" in validator().reasons(row)


@pytest.mark.parametrize(
    "field,value", [("votos_validos", 1000000), ("votos_nulos", 80)]
)
def test_individual_arithmetic_impossibilities_are_rejected(field, value):
    rows = results()
    rows[0][field] = value
    assert not validator("resultados_historicos").run(rows).valid


def test_discovery_obeys_alternative_source_path(tmp_path, monkeypatch):
    folder = tmp_path / "alternative"
    folder.mkdir()
    (folder / "padron_20260303.csv").write_text("id\n1", encoding="utf-8")
    cfg = settings.load_config()
    cfg["sources"]["empadronados"]["path_pattern"] = str(folder / "padron_{fecha}.csv")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    monkeypatch.setattr(settings, "CONFIG_PATH", path)
    assert snapshot_files() == [("2026-03-03", folder / "padron_20260303.csv")]
    cfg["quality"]["on_reject"] = "fail"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(ValueError, match="solo admite"):
        settings.load_config()


def test_alternative_components_satisfy_public_pipeline_contract(tmp_path, monkeypatch):
    import src.pipelines.base_pipeline as module

    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    class Extractor(BaseExtractor):
        def extract(self):
            return [{"id": "1"}]

        def metadata(self):
            return {**super().metadata(), "sha256": hashlib.sha256(b"1").hexdigest()}

    class Transformer:
        def transform(self, rows):
            return rows

    class Loader(BaseLoader):
        def load(self, records, *, conn=None):
            self.metrics = {
                "insertadas": len(records),
                "actualizadas": 0,
                "sin_cambios": 0,
            }
            return len(records)

    class Store:
        @contextmanager
        def transaction(self):
            yield object()

        def record_success(self, *args):
            pass

    class Validator:
        def run(self, rows):
            return ValidationResult(valid=rows)

    p = Pipeline(
        "alternative",
        {},
        Extractor(),
        Transformer(),
        Loader(),
        lambda _: Validator(),
        Store(),
    )
    assert p.run()["cargadas"] == 1
