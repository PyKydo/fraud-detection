import hashlib
import logging
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

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

PII_COLUMNS = ["cc_num", "first", "last", "street"]
FECHA_COLUMNA = "trans_date_trans_time"


def load_raw_dataset() -> pd.DataFrame:
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No se encontro dataset en {RAW_DIR}")
    filepath = csv_files[0]
    logger.info("Cargando dataset desde %s", filepath.name)
    df = pd.read_csv(filepath)
    logger.info("Dataset cargado: %d filas, %d columnas", len(df), len(df.columns))
    return df


def analizar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("=== INICIO: Analisis de valores nulos ===")
    nulos_por_columna = df.isnull().sum()
    columnas_con_nulos = nulos_por_columna[nulos_por_columna > 0]

    if columnas_con_nulos.empty:
        logger.info("No se detectaron valores nulos en el dataset")
        return df

    for col, nulos in columnas_con_nulos.items():
        pct = (nulos / len(df)) * 100
        logger.warning("Columna '%s': %d nulos (%.2f%%)", col, nulos, pct)

    logger.info("Total de filas con al menos 1 nulo: %d", df.isnull().any(axis=1).sum())
    logger.info("=== FIN: Analisis de valores nulos ===")
    return df


def imputar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("=== INICIO: Imputacion de valores nulos ===")
    filas_antes = len(df)

    estrategias = {}
    for col in df.columns:
        if df[col].isnull().sum() == 0:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].median())
            estrategias[col] = "mediana"
            logger.info("Imputando '%s' (numerica) con mediana: %.2f", col, df[col].median())

        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].fillna(method="ffill")
            estrategias[col] = "forward-fill"
            logger.info("Imputando '%s' (datetime) con forward-fill", col)

        else:
            df[col] = df[col].fillna("DESCONOCIDO")
            estrategias[col] = "DESCONOCIDO"
            logger.info("Imputando '%s' (categorica) con 'DESCONOCIDO'", col)

    filas_restantes_con_nulos = df.isnull().any(axis=1).sum()
    if filas_restantes_con_nulos > 0:
        df = df.dropna()
        logger.warning("Eliminadas %d filas con nulos residuales", filas_restantes_con_nulos)

    logger.info("Filas antes: %d | Filas despues: %d", filas_antes, len(df))
    logger.info("=== FIN: Imputacion de valores nulos ===")
    return df


def corregir_fechas(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("=== INICIO: Correccion de formato datetime ===")
    if FECHA_COLUMNA not in df.columns:
        logger.warning("Columna '%s' no encontrada. Omitiendo conversion.", FECHA_COLUMNA)
        return df

    try:
        df[FECHA_COLUMNA] = pd.to_datetime(df[FECHA_COLUMNA], errors="coerce")
        nulos_fecha = df[FECHA_COLUMNA].isnull().sum()
        if nulos_fecha > 0:
            logger.warning("%d fechas invalidas convertidas a NaT", nulos_fecha)
            df[FECHA_COLUMNA] = df[FECHA_COLUMNA].fillna(method="ffill")
            logger.info("NaT imputadas con forward-fill")
        logger.info("Columna '%s' convertida a datetime. Rango: %s -> %s",
                    FECHA_COLUMNA, df[FECHA_COLUMNA].min(), df[FECHA_COLUMNA].max())
    except Exception:
        logger.exception("Error al convertir '%s' a datetime", FECHA_COLUMNA)

    logger.info("=== FIN: Correccion de formato datetime ===")
    return df


def enmascarar_pii(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica SHA-256 a columnas PII segun Ley N° 19.628 (Proteccion de Datos Personales, Chile).

    Columnas enmascaradas: cc_num, first, last, street.
    """

    logger.info("=== INICIO: Enmascaramiento PII (Ley 19.628) ===")
    columnas_presentes = [c for c in PII_COLUMNS if c in df.columns]
    columnas_faltantes = [c for c in PII_COLUMNS if c not in df.columns]

    if columnas_faltantes:
        logger.warning("Columnas PII no encontradas: %s", columnas_faltantes)

    for col in columnas_presentes:
        df[col] = df[col].astype(str).apply(
            lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()
        )
        logger.info("Columna '%s' enmascarada con SHA-256", col)

    logger.info("Columnas enmascaradas: %s", columnas_presentes)
    logger.info("Cumplimiento: Ley Ndeg 19.628 - Proteccion de Datos Personales (Chile)")
    logger.info("=== FIN: Enmascaramiento PII ===")
    return df


def guardar_dataset(df: pd.DataFrame) -> Path:
    output_path = PROCESSED_DIR / "02_cleaned_data.parquet"
    df.to_parquet(output_path, index=False)
    logger.info("Dataset limpio y enmascarado guardado en %s (%d filas)", output_path, len(df))
    return output_path


def main() -> pd.DataFrame:
    logger.info("=== INICIO PIPELINE: 02_cleaning ===")
    try:
        df = load_raw_dataset()
        analizar_nulos(df)
        df = imputar_nulos(df)
        df = corregir_fechas(df)
        df = enmascarar_pii(df)
        output = guardar_dataset(df)
    except FileNotFoundError:
        logger.error("Dataset no encontrado en %s. Abortando limpieza.", RAW_DIR)
        raise
    except Exception:
        logger.exception("Error critico en etapa de limpieza. Abortando pipeline.")
        raise
    logger.info("=== FIN PIPELINE: 02_cleaning === (%s)", output.name)
    return df


if __name__ == "__main__":
    main()
