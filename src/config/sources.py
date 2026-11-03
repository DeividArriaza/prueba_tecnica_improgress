"""Rutas y descubrimiento comparten la misma configuración de fuente."""

from datetime import datetime, date
from pathlib import Path
import re
from src.config.settings import PROJECT_ROOT, load_config


def parse_cutoff(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("La fecha debe tener formato YYYY-MM-DD")
    return parsed


def snapshot_files(source="empadronados"):
    pattern = load_config()["sources"][source]["path_pattern"]
    template = PROJECT_ROOT / pattern
    if template.name.count("{fecha}") != 1 or "{fecha}" in str(template.parent):
        raise ValueError(
            "path_pattern requiere un único {fecha} en el nombre del archivo"
        )
    matcher = re.compile(
        re.escape(template.name).replace(re.escape("{fecha}"), r"([0-9]{8})")
    )
    found = []
    for path in template.parent.glob(template.name.replace("{fecha}", "????????")):
        match = matcher.fullmatch(path.name)
        if match and path.is_file():
            cutoff = datetime.strptime(match[1], "%Y%m%d").date().isoformat()
            found.append((cutoff, path))
    return sorted(found)


def source_path(source, fecha=None):
    config = load_config()["sources"][source]
    if fecha is None:
        return PROJECT_ROOT / config["path"]
    parse_cutoff(fecha)
    return PROJECT_ROOT / config["path_pattern"].format(fecha=fecha.replace("-", ""))
