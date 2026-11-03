"""Carga transaccional por lotes sobre el DDL original, sin nuevas restricciones."""

import json
from datetime import datetime, timezone
from psycopg2 import sql
from psycopg2.extras import execute_values
from src.loaders.base import BaseLoader


def table_identifier(table):
    return sql.Identifier(*table.split("."))


def merge(conn, table, key, columns, rows):
    if not rows:
        return {"insertadas": 0, "actualizadas": 0, "sin_cambios": 0}
    target = table_identifier(table)
    cols = sql.SQL(",").join(map(sql.Identifier, columns))
    # Las claves ya fueron validadas como no nulas. Igualdad permite hash joins.
    match = sql.SQL(" AND ").join(
        sql.SQL("t.{} = s.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in key
    )
    attrs = [c for c in columns if c not in key]
    with conn.cursor() as cur:
        # También impide que un escritor externo inserte durante nuestra comparación.
        cur.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(target))
        cur.execute(
            sql.SQL(
                "CREATE TEMP TABLE etl_stage ON COMMIT DROP AS SELECT {} FROM {} WITH NO DATA"
            ).format(cols, target)
        )
        execute_values(
            cur,
            "INSERT INTO etl_stage VALUES %s",
            [[None if r.get(c) is None else str(r[c]) for c in columns] for r in rows],
            page_size=1000,
        )
        cur.execute(
            sql.SQL(
                "SELECT 1 FROM {} t JOIN etl_stage s ON {} GROUP BY {} HAVING count(*) > 1 LIMIT 1"
            ).format(
                target,
                match,
                sql.SQL(",").join(
                    sql.SQL("s.{}").format(sql.Identifier(k)) for k in key
                ),
            )
        )
        if cur.fetchone():
            raise ValueError(
                f"El destino {table} ya contiene claves duplicadas; revisar antes de cargar"
            )
        assignments = sql.SQL(",").join(
            sql.SQL("{}=s.{}").format(sql.Identifier(c), sql.Identifier(c))
            for c in attrs
        )
        differences = sql.SQL(" OR ").join(
            sql.SQL("t.{} IS DISTINCT FROM s.{}").format(
                sql.Identifier(c), sql.Identifier(c)
            )
            for c in attrs
        )
        cur.execute(
            sql.SQL("UPDATE {} t SET {} FROM etl_stage s WHERE {} AND ({})").format(
                target, assignments, match, differences
            )
        )
        updated = cur.rowcount
        cur.execute(
            sql.SQL(
                "INSERT INTO {} ({}) SELECT {} FROM etl_stage s WHERE NOT EXISTS (SELECT 1 FROM {} t WHERE {})"
            ).format(target, cols, cols, target, match)
        )
        inserted = cur.rowcount
        cur.execute("DROP TABLE etl_stage")
    return {
        "insertadas": inserted,
        "actualizadas": updated,
        "sin_cambios": len(rows) - inserted - updated,
    }


def watermark(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT observacion FROM electoral.carga_log WHERE proceso='watermark:empadronados' ORDER BY id_log DESC LIMIT 1"
        )
        row = cur.fetchone()
    return json.loads(row[0])["fecha"] if row else None


class FullLoader(BaseLoader):
    def __init__(self, config):
        super().__init__()
        self.config = config

    def load(self, records, conn=None):
        if conn is None:
            raise ValueError("El loader necesita una transacción del pipeline")
        rows = list(records)
        columns = list(self.config["columns"])
        self.metrics = merge(
            conn, self.config["target_table"], self.config["natural_key"], columns, rows
        )
        if rows and "codigo_mesa" in rows[0]:
            mesas = {
                r["codigo_mesa"]: {
                    "codigo_mesa": r["codigo_mesa"],
                    "codigo_centro_votacion": r["codigo_centro_votacion"],
                    "numero_mesa": r["codigo_mesa"].rsplit("-", 1)[1],
                }
                for r in rows
            }
            merge(
                conn,
                "electoral.mesas_votacion",
                ["codigo_mesa"],
                ["codigo_mesa", "codigo_centro_votacion", "numero_mesa"],
                list(mesas.values()),
            )
        # fechaCarga es un identificador SQL no entrecomillado: PostgreSQL lo guarda en minúscula.
        timestamp_column = self.config.get("timestamp_column")
        if timestamp_column:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("UPDATE {} SET {}=%s WHERE {} IS NULL").format(
                        table_identifier(self.config["target_table"]),
                        sql.Identifier(timestamp_column),
                        sql.Identifier(timestamp_column),
                    ),
                    (datetime.now(timezone.utc).isoformat(),),
                )
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE electoral.mesas_votacion SET fechacarga=%s WHERE fechacarga IS NULL",
                (datetime.now(timezone.utc).isoformat(),),
            )
        return self.metrics["insertadas"] + self.metrics["actualizadas"]


class IncrementalLoader(FullLoader):
    def __init__(self, config, fecha):
        super().__init__(config)
        self.fecha = fecha

    def load(self, records, conn=None):
        latest = watermark(conn)
        if latest and self.fecha < latest:
            raise ValueError(
                f"Fecha {self.fecha} anterior al watermark {latest}; usar rebuild-padron --hasta {latest} para reprocesar sin retroceder"
            )
        return super().load(records, conn=conn)
