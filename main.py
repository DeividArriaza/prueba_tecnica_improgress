"""Punto de entrada del ETL.

Ejemplos de uso esperado:
    python main.py load-historico
    python main.py load-empadronados --fecha 2026-03-02
    python main.py load-empadronados --fecha 2026-03-03

Puedes cambiar la interfaz del CLI si lo justificas, pero debe permitir
ejecutar la carga histórica y una fecha específica del padrón (backfill).
"""
from __future__ import annotations

import argparse

from src.utils.logger import get_logger

logger = get_logger("main")


def cmd_load_historico(args: argparse.Namespace) -> None:
    from src.pipelines.historico_pipeline import (
        build_centros_pipeline,
        build_resultados_pipeline,
    )

    build_centros_pipeline().run()
    build_resultados_pipeline().run()


def cmd_load_empadronados(args: argparse.Namespace) -> None:
    from src.pipelines.empadronados_pipeline import build_empadronados_pipeline

    build_empadronados_pipeline(args.fecha).run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ETL electoral")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("load-historico", help="Carga única de data histórica")
    p1.set_defaults(func=cmd_load_historico)

    p2 = sub.add_parser("load-empadronados", help="Carga incremental del padrón")
    p2.add_argument("--fecha", required=True, help="Fecha de proceso YYYY-MM-DD")
    p2.set_defaults(func=cmd_load_empadronados)

    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
