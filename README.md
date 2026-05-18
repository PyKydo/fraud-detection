# Fraud Detection - Pipeline DataOps

Evaluacion Parcial 2 - Gestion de Datos para IA (Duoc UC)

Pipeline automatizado para deteccion de fraude en tarjetas de credito, aplicando metodologia hibrida PMBOK/Agile con enfoque DataOps.

## Stack Tecnologico

| Componente | Tecnologia |
|-----------|-----------|
| Lenguaje | Python 3.10 |
| Contenedor | Docker (python:3.10-slim) |
| Procesamiento | Pandas, NumPy |
| Validacion | Great Expectations, Pydantic |
| Logging | `logging` (stdlib) |
| Gestion | Trello + GitHub |

## Arquitectura del Pipeline

```
data/raw/ ──► 01_ingestion ──► 02_cleaning ──► 03_validation ──► 04_loading ──► data/processed/
                  │                │                │                │
                  └─── logs/pipeline.log ──────────┘                │
                                                            
```

### Etapas

| Script | Funcion | Estado |
|--------|---------|--------|
| `01_ingestion.py` | Carga de datos crudos, validacion de archivo, manejo de excepciones | Implementado |
| `02_cleaning.py` | Imputacion de nulos, enmascaramiento PII (Ley 19.628) | Pendiente |
| `03_validation.py` | Validacion estructural y semantica (Great Expectations/Pydantic) | Pendiente |
| `04_loading.py` | Exportacion de datos procesados a `data/processed/` | Pendiente |

## Estructura del Repositorio

```
.
├── data/
│   ├── raw/           # Dataset original (ignorado en git)
│   └── processed/     # Datos limpios y enmascarados (ignorado en git)
├── src/
│   ├── 01_ingestion.py
│   ├── 02_cleaning.py
│   ├── 03_validation.py
│   └── 04_loading.py
├── logs/              # Registros del pipeline (ignorado en git)
├── docs/              # Informe tecnico y recursos PMBOK
├── Dockerfile
├── requirements.txt
└── .gitignore
```

## Ejecucion

```bash
# Construir imagen
docker build -t fraud-detection .

# Ejecutar pipeline completo
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  fraud-detection python src/01_ingestion.py
```

## Dataset

- **Origen**: Fraud Detection Dataset (Kaggle)
- **Filas**: 555,719 transacciones
- **Columnas**: 23 (trans_date_trans_time, cc_num, merchant, category, amt, first, last, gender, street, city, state, zip, lat, long, city_pop, job, dob, trans_num, unix_time, merch_lat, merch_long, is_fraud)
- **Variable objetivo**: `is_fraud` (0: legitima, 1: fraude)

## Cumplimiento Normativo

Este proyecto aplica la **Ley Ndeg 19.628** de Proteccion de Datos Personales (Chile) mediante tecnicas de hashing/enmascaramiento sobre columnas PII (`cc_num`, `first`, `last`, `street`).
