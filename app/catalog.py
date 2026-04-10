from __future__ import annotations

import json
from pathlib import Path


DEFAULT_CATALOG = [
    {"sku": "SKU-DES-001", "name": "Desarmador", "class_name": "Desarmador"},
    {"sku": "SKU-PER-001", "name": "Perno", "class_name": "Perno"},
    {"sku": "SKU-PIN-001", "name": "Pinza", "class_name": "Pinza"},
    {"sku": "SKU-RON-001", "name": "Rondana", "class_name": "Rondana"},
    {"sku": "SKU-TUE-001", "name": "Tuerca", "class_name": "Tuerca"},
]


def load_catalog(catalog_path: Path) -> list[dict[str, str]]:
    if not catalog_path.exists():
        catalog_path.write_text(
            json.dumps(DEFAULT_CATALOG, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return DEFAULT_CATALOG

    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("El catalogo debe ser una lista JSON de productos.")

    catalog: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Cada entrada del catalogo debe ser un objeto JSON.")

        sku = str(item["sku"]).strip()
        name = str(item["name"]).strip()
        class_name = str(item["class_name"]).strip()

        if not sku or not name or not class_name:
            raise ValueError("Las entradas del catalogo no pueden tener campos vacios.")

        catalog.append({"sku": sku, "name": name, "class_name": class_name})

    return catalog
