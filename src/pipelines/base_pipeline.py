"""Orquestación interna de un flujo: extract -> transform -> validate -> load.

El pipeline no sabe de CSV ni de PostgreSQL: recibe los componentes ya
construidos. Eso es lo que permite cambiar una fuente o un destino sin
tocar esta clase.
"""
from __future__ import annotations

from datetime import datetime

from src.extractors.base import BaseExtractor
from src.loaders.base import BaseLoader
from src.quality.validations import Validator
from src.transformers.base import BaseTransformer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Pipeline:
    name: str = "pipeline"

    def __init__(
        self,
        extractor: BaseExtractor,
        transformer: BaseTransformer,
        loader: BaseLoader,
        validator: Validator | None = None,
    ) -> None:
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        self.validator = validator

    def run(self) -> dict:
        started = datetime.now()
        logger.info("[%s] inicio", self.name)

        records = self.extractor.extract()
        records = self.transformer.transform(records)

        rejected = 0
        if self.validator:
            result = self.validator.run(records)
            records = result.valid
            rejected = len(result.rejected)
            # TODO (candidato): ¿qué haces con result.rejected?
            logger.info("[%s] calidad: %s", self.name, result.summary)

        loaded = self.loader.load(records)
        elapsed = (datetime.now() - started).total_seconds()

        metrics = {
            "pipeline": self.name,
            "cargados": loaded,
            "rechazados": rejected,
            "segundos": round(elapsed, 2),
        }
        logger.info("[%s] fin %s", self.name, metrics)
        # TODO (candidato): persistir estas métricas (¿carga_log? ¿tabla nueva?)
        return metrics
