"""Construcción configurable; agregar una fuente no modifica Pipeline."""

from datetime import date
from src.config.settings import PROJECT_ROOT, load_config
from src.config.sources import source_path, parse_cutoff
from src.extractors.csv_extractor import CSVExtractor
from src.transformers.base import BaseTransformer, TransformerPipeline
from src.transformers.common import (
    TrimStrings,
    NormalizeText,
    CastNumeric,
    ParseDates,
    StandardizeCategories,
    Deduplicate,
)
from src.loaders.postgres_loader import FullLoader, IncrementalLoader
from src.pipelines.base_pipeline import Pipeline
from src.quality.business import BusinessValidator
from src.utils.run_store import PostgresRunStore


class ElectionDefaults(BaseTransformer):
    def transform(self, records):
        for source in records:
            row = dict(source)
            # Una vuelta vacía en elecciones de una sola ronda equivale a ronda 1.
            if row.get("vuelta") is None and row.get("tipo_eleccion") in (
                "legislativa",
                "municipal",
            ):
                row["vuelta"] = "1"
            yield row


def build_pipeline(name, fecha=None):
    cfg = load_config()
    source = cfg["sources"][name]
    path = source_path(name, fecha)
    transforms = [
        TrimStrings(),
        NormalizeText(source["text_fields"]),
        StandardizeCategories(cfg["categories"]),
    ]
    if name == "resultados_historicos":
        transforms.append(ElectionDefaults())
    transforms.extend(
        [
            CastNumeric(source["numeric_fields"], source["decimal_fields"]),
            ParseDates(source["date_fields"]),
            Deduplicate(source["natural_key"]),
        ]
    )
    loader = (
        IncrementalLoader(source, fecha)
        if source["load_mode"] == "incremental"
        else FullLoader(source)
    )
    cutoff = date.fromisoformat(fecha) if fecha else date.today()
    validator_factory = lambda catalog: BusinessValidator(
        name, source["natural_key"], catalog, cutoff
    )
    return Pipeline(
        name,
        source,
        CSVExtractor(PROJECT_ROOT / path, required_columns=source["columns"]),
        TransformerPipeline(*transforms),
        loader,
        validator_factory,
        PostgresRunStore(),
        fecha,
    )
