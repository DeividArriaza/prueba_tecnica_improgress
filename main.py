"""Interfaz reproducible del ETL electoral."""

import argparse
from datetime import date, timedelta
import json
from src.pipelines.factory import build_pipeline
from src.quality.business import BusinessValidator
from src.config.sources import snapshot_files, parse_cutoff
from src.pipelines.rebuild_pipeline import rebuild_padron


def catalog_from_files():
    pipeline = build_pipeline("centros_votacion")
    rows = [
        r
        for r in pipeline.transformer.transform(pipeline.extractor.extract())
        if not r.get("_duplicate")
    ]
    valid = (
        BusinessValidator(
            "centros_votacion", pipeline.config["natural_key"], {}, date.today()
        )
        .run(rows)
        .valid
    )
    return {r["codigo_centro_votacion"]: r for r in valid}


def run_historico():
    return [
        build_pipeline(name).run()
        for name in ("centros_votacion", "resultados_historicos")
    ]


def run_empadronados(fecha):
    return build_pipeline("empadronados", fecha).run()


def main():
    parser = argparse.ArgumentParser(description="ETL electoral")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("load-historico")
    padr = sub.add_parser("load-empadronados")
    padr.add_argument("--fecha", required=True)
    check = sub.add_parser(
        "validate", help="Valida archivos sin conectarse a PostgreSQL"
    )
    check.add_argument(
        "--fecha", help="Fecha del padrón; omitir para validar todas las fuentes"
    )
    back = sub.add_parser("backfill")
    back.add_argument("--desde", required=True)
    back.add_argument("--hasta", required=True)
    rebuild = sub.add_parser(
        "rebuild-padron",
        help="Reconstruye todos los snapshots hasta una fecha y publica atómicamente",
    )
    rebuild.add_argument("--hasta", required=True)
    args = parser.parse_args()
    if args.command == "load-historico":
        result = run_historico()
    elif args.command == "load-empadronados":
        result = run_empadronados(args.fecha)
    elif args.command == "validate":
        catalog = catalog_from_files()
        available = [value for value, _ in snapshot_files()]
        jobs = (
            [("empadronados", args.fecha)]
            if args.fecha
            else [("centros_votacion", None), ("resultados_historicos", None)]
            + [("empadronados", value) for value in available]
        )
        result = [
            build_pipeline(name, fecha).run(dry_run=True, catalog=catalog)
            for name, fecha in jobs
        ]
    elif args.command == "rebuild-padron":
        result = rebuild_padron(args.hasta)
    else:
        current, end = parse_cutoff(args.desde), parse_cutoff(args.hasta)
        if current > end:
            parser.error("--desde debe ser menor o igual a --hasta")
        result = []
        while current <= end:
            result.append(run_empadronados(current.isoformat()))
            current += timedelta(days=1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
