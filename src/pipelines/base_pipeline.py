"""Coordina lectura, limpieza, validación y carga; conserva evidencia por ejecución."""

from contextlib import nullcontext
import json
from time import perf_counter
from uuid import uuid4
from src.config.settings import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Pipeline:
    def __init__(
        self,
        name,
        config,
        extractor,
        transformer,
        loader,
        validator_factory,
        store,
        fecha=None,
    ):
        self.name, self.config = name, config
        self.extractor, self.transformer, self.loader = extractor, transformer, loader
        self.fecha = fecha
        self.validator_factory, self.store = validator_factory, store

    def run(self, dry_run=False, catalog=None, *, connection=None, audit_name=None):
        started = perf_counter()
        run_id = uuid4().hex
        folder = PROJECT_ROOT / "output" / run_id
        folder.mkdir(parents=True)
        metrics = {
            "run_id": run_id,
            "pipeline": self.name,
            "fecha": self.fecha,
            "estado": "iniciado",
            "leidas": 0,
            "validas": 0,
            "rechazadas": 0,
            "duplicadas": 0,
            "cargadas": 0,
        }
        try:
            raw = list(self.extractor.extract())
            metrics["leidas"] = len(raw)
            digest = self.extractor.metadata()["sha256"]
            rows = list(self.transformer.transform(raw))
            metrics["duplicadas"] = sum(bool(r.get("_duplicate")) for r in rows)
            rows = [r for r in rows if not r.get("_duplicate")]
            context = (
                nullcontext(None)
                if dry_run
                else (
                    nullcontext(connection)
                    if connection is not None
                    else self.store.transaction()
                )
            )
            with context as conn:
                if not dry_run and self.config.get("requires_catalog"):
                    catalog = self.store.catalog(conn)
                result = self.validator_factory(catalog or {}).run(rows)
                metrics.update(
                    validas=len(result.valid),
                    rechazadas=len(result.rejected),
                    sha256=digest,
                )
                warnings = [r for r in result.valid if r.get("_warnings")]
                metrics["advertencias"] = len(warnings)
                with (folder / "warnings.jsonl").open("w", encoding="utf-8") as stream:
                    for row in warnings:
                        stream.write(
                            json.dumps(
                                {
                                    "linea": row.get("_line"),
                                    "motivos": row["_warnings"],
                                    "original": row.get("_raw", row),
                                },
                                ensure_ascii=False,
                                default=str,
                            )
                            + "\n"
                        )
                with (folder / "quarantine.jsonl").open(
                    "w", encoding="utf-8"
                ) as stream:
                    for row, reason in result.rejected:
                        stream.write(
                            json.dumps(
                                {
                                    "linea": row.get("_line"),
                                    "motivo": reason,
                                    "original": row.get("_raw", row),
                                    "transformado": {
                                        k: v
                                        for k, v in row.items()
                                        if not k.startswith("_")
                                    },
                                },
                                ensure_ascii=False,
                                default=str,
                            )
                            + "\n"
                        )
                if (
                    metrics["leidas"]
                    != metrics["validas"]
                    + metrics["rechazadas"]
                    + metrics["duplicadas"]
                ):
                    raise AssertionError("Las cantidades no concilian")
                if not result.valid:
                    raise ValueError(
                        "Fuente vacía o sin filas válidas; no se carga ni avanza watermark"
                    )
                if not dry_run:
                    metrics["cargadas"] = self.loader.load(result.valid, conn=conn)
                    metrics.update(self.loader.metrics)
                    metrics["segundos"] = round(perf_counter() - started, 3)
                    self.store.record_success(
                        conn, audit_name or self.name, self.fecha, digest, metrics
                    )
            metrics["estado"] = (
                "validado"
                if dry_run
                else ("pendiente_commit" if connection is not None else "ok")
            )
            return metrics
        except Exception as exc:
            metrics.update(
                estado="error", error=str(exc), cargadas=0, insertadas=0, actualizadas=0
            )
            raise
        finally:
            metrics["segundos"] = round(perf_counter() - started, 3)
            (folder / "metrics.json").write_text(
                json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("%s", json.dumps(metrics, ensure_ascii=False))
