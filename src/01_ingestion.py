import logging
import os
import sys
from pathlib import Path

import pandas as pd

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def find_dataset(raw_dir: Path) -> Path:
    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No se encontro ningun archivo .csv en {raw_dir}")
    return csv_files[0]


def load_dataset(filepath: Path) -> pd.DataFrame:
    logger.info("Iniciando carga del dataset desde %s", filepath.name)
    try:
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        logger.error("El archivo %s esta vacio (0 bytes)", filepath.name)
        raise
    except Exception:
        logger.exception("Error inesperado al leer %s", filepath.name)
        raise
    logger.info("Dataset cargado exitosamente: %d filas, %d columnas",
                len(df), len(df.columns))
    return df


def validate_not_empty(df: pd.DataFrame, filepath: Path) -> None:
    if df.empty:
        raise ValueError(f"El dataset {filepath.name} no contiene registros")
    logger.info("Validacion de contenido: dataset no vacio")


def main() -> pd.DataFrame:
    logger.info("=== INICIO PIPELINE: 01_ingestion ===")
    try:
        filepath = find_dataset(RAW_DIR)
        logger.info("Archivo detectado: %s (%.2f MB)",
                    filepath.name, filepath.stat().st_size / (1024 * 1024))
        df = load_dataset(filepath)
        validate_not_empty(df, filepath)
    except FileNotFoundError:
        logger.error("No se encontro dataset en %s. Abortando ingesta.", RAW_DIR)
        raise
    except Exception:
        logger.exception("Error critico en etapa de ingesta. Abortando pipeline.")
        raise
    logger.info("=== FIN PIPELINE: 01_ingestion === (%d filas procesadas)", len(df))
    return df


if __name__ == "__main__":
    df_result = main()
