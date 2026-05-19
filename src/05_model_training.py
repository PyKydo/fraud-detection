import numpy as np
from pathlib import Path

import joblib
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
from xgboost import XGBClassifier

from logger_config import setup_logging

logger = setup_logging(__name__)

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODELS_DIR / "xgboost_fraud_model.joblib"

COLUMNAS_A_DESCARTAR = [
    "trans_date_trans_time",
    "trans_num",
    "dob",
    "unix_time",
    "cc_num",
    "first",
    "last",
    "street",
]

COLUMNAS_NECESARIAS = ["lat", "long", "merch_lat", "merch_long", "trans_date_trans_time"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def feature_engineering(df: pd.DataFrame, cat_means: dict | None = None) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    nuevas = {}

    if all(c in df.columns for c in ["lat", "long", "merch_lat", "merch_long"]):
        df["dist_km"] = df.apply(
            lambda r: haversine_km(r["lat"], r["long"], r["merch_lat"], r["merch_long"]), axis=1
        )
        nuevas["dist_km"] = "Distancia cliente-comercio (Haversine km)"

    if "trans_date_trans_time" in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df["trans_date_trans_time"]):
            df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"])
        df["hora"] = df["trans_date_trans_time"].dt.hour
        df["dia_semana"] = df["trans_date_trans_time"].dt.dayofweek
        nuevas["hora"] = "Hora del dia (0-23)"
        nuevas["dia_semana"] = "Dia de la semana (0=Lunes)"

    if "category" in df.columns and "amt" in df.columns:
        if cat_means is None:
            cat_means = df.groupby("category")["amt"].mean().to_dict()
        df["amt_vs_cat_mean"] = df.apply(
            lambda r: r["amt"] - cat_means.get(r["category"], r["amt"]), axis=1
        )
        nuevas["amt_vs_cat_mean"] = "Diferencia vs monto promedio de la categoria"

    logger.info("Feature engineering: %d nuevas variables generadas", len(nuevas))
    for col, desc in nuevas.items():
        logger.info("  - %s: %s", col, desc)

    return df, cat_means


def cargar_datos() -> pd.DataFrame:
    input_path = PROCESSED_DIR / "04_produccion.parquet"
    if not input_path.exists():
        raise FileNotFoundError(f"No se encontro {input_path}")
    logger.info("Cargando datos de produccion desde %s", input_path.name)
    df = pd.read_parquet(input_path)
    logger.info("Dataset cargado: %d filas, %d columnas", len(df), len(df.columns))
    return df


def split_temporal(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    columna_fecha = "trans_date_trans_time"
    if columna_fecha not in df.columns:
        raise KeyError(f"Columna '{columna_fecha}' requerida para split cronologico")
    df = df.sort_values(columna_fecha)
    corte = int(len(df) * 0.8)
    df_train = df.iloc[:corte]
    df_test = df.iloc[corte:]
    logger.info("Split temporal: Train %d filas (hasta %s), Test %d filas (desde %s)",
                len(df_train), df_train[columna_fecha].max(),
                len(df_test), df_test[columna_fecha].min())
    return df_train, df_test


def preparar_features(df: pd.DataFrame, cat_means: dict | None = None) -> tuple[pd.DataFrame, pd.Series, dict]:
    df, cat_means = feature_engineering(df, cat_means)
    columnas_descartar = [c for c in COLUMNAS_A_DESCARTAR if c in df.columns]
    y = df["is_fraud"] if "is_fraud" in df.columns else None
    X = df.drop(columns=["is_fraud"] + columnas_descartar, errors="ignore")
    return X, y, cat_means


def convertir_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype("category")
    return df


def codificar_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_categorical_dtype(df[col]):
            df[col] = df[col].cat.codes
        elif df[col].dtype == "object":
            df[col] = df[col].astype("category").cat.codes
    return df


def balancear_smote(X_train: pd.DataFrame, y_train: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    conteo = y_train.value_counts()
    logger.info("Antes de SMOTE - clase 0: %d, clase 1: %d (ratio: %.1f:1)",
                conteo.get(0, 0), conteo.get(1, 0), conteo.get(0, 0) / max(conteo.get(1, 0), 1))

    smote = SMOTE(sampling_strategy=0.1, k_neighbors=3, random_state=42)
    X_res, y_res = smote.fit_resample(X_train, y_train)

    conteo_res = y_res.value_counts()
    logger.info("Post SMOTE - clase 0: %d, clase 1: %d (ratio: %.1f:1)",
                conteo_res.get(0, 0), conteo_res.get(1, 0), conteo_res.get(0, 0) / max(conteo_res.get(1, 0), 1))
    return X_res, y_res


def entrenar_modelo(X_train: pd.DataFrame, y_train: pd.Series) -> XGBClassifier:
    ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    logger.info("Ratio de desbalance post-SMOTE: %.2f", ratio)

    modelo = XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.03,
        random_state=42,
        eval_metric="aucpr",
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=2.0,
        max_delta_step=1,
    )
    logger.info("Entrenando XGBoost (eval_metric=aucpr, %d arboles)", modelo.n_estimators)
    modelo.fit(X_train, y_train)
    logger.info("Entrenamiento completado")
    return modelo


def evaluar_modelo(modelo: XGBClassifier, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = modelo.predict(X_test)
    y_proba = modelo.predict_proba(X_test)[:, 1]

    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    accuracy = (y_pred == y_test).mean()

    logger.info("=== Metricas del Modelo (umbral=0.5) ===")
    logger.info("Accuracy:  %.4f", accuracy)
    logger.info("Precision: %.4f", precision)
    logger.info("Recall:    %.4f", recall)
    logger.info("F1-Score:  %.4f", f1)
    logger.info("Classification Report:\n%s", classification_report(y_test, y_pred, digits=4))

    y_pred_th = (y_proba >= 0.25).astype(int)
    recall_th = recall_score(y_test, y_pred_th)
    f1_th = f1_score(y_test, y_pred_th)
    precision_th = precision_score(y_test, y_pred_th)
    logger.info("=== Metricas del Modelo (umbral=0.25) ===")
    logger.info("Precision: %.4f", precision_th)
    logger.info("Recall:    %.4f", recall_th)
    logger.info("F1-Score:  %.4f", f1_th)

    return {
        "recall": recall, "f1_score": f1, "precision": precision, "accuracy": accuracy,
        "recall_th": recall_th, "f1_th": f1_th, "precision_th": precision_th,
    }


def guardar_modelo(modelo: XGBClassifier) -> Path:
    joblib.dump(modelo, MODEL_PATH)
    logger.info("Modelo guardado en %s (%.2f MB)", MODEL_PATH, MODEL_PATH.stat().st_size / (1024 * 1024))
    return MODEL_PATH


def main() -> None:
    logger.info("=== INICIO PIPELINE: 05_model_training ===")
    try:
        df = cargar_datos()
        df_train, df_test = split_temporal(df)

        X_train, y_train, cat_means = preparar_features(df_train)
        X_test, y_test, _ = preparar_features(df_test, cat_means)

        X_train = codificar_categoricas(X_train)
        X_test = codificar_categoricas(X_test)

        X_train, y_train = balancear_smote(X_train, y_train)

        modelo = entrenar_modelo(X_train, y_train)
        metricas = evaluar_modelo(modelo, X_test, y_test)
        guardar_modelo(modelo)

        logger.info("=== RESUMEN FINAL ===")
        logger.info("Recall (umbral=0.5): %.4f | F1: %.4f | Precision: %.4f",
                    metricas["recall"], metricas["f1_score"], metricas["precision"])
        logger.info("Recall (umbral=0.25): %.4f | F1: %.4f | Precision: %.4f",
                    metricas["recall_th"], metricas["f1_th"], metricas["precision_th"])
    except FileNotFoundError:
        logger.error("Archivo de datos no encontrado. Abortando entrenamiento.")
        raise
    except Exception:
        logger.exception("Error critico en entrenamiento. Abortando pipeline.")
        raise
    logger.info("=== FIN PIPELINE: 05_model_training ===")


if __name__ == "__main__":
    main()
