from hashlib import sha256
import pytest
from src.extractors.csv_extractor import CSVExtractor


def test_csv_preserves_codes_and_tracks_exact_checksum(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text('codigo,nombre\n0101,"Primera, oficina"\n', encoding="utf-8-sig")
    extractor = CSVExtractor(path, required_columns=["codigo", "nombre"])
    rows = list(extractor.extract())
    assert rows[0]["codigo"] == "0101"
    assert rows[0]["nombre"] == "Primera, oficina"
    assert extractor.metadata()["sha256"] == sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "content", ["codigo,codigo\n01,02\n", "codigo,nombre\n01,X,Y\n", "codigo\n01\n"]
)
def test_bad_csv_fails_instead_of_silently_losing_columns(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        list(CSVExtractor(path, required_columns=["codigo", "nombre"]).extract())
