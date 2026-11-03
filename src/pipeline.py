"""Un solo comando desde los datos crudos hasta los modelos guardados.

    python -m src.pipeline                    # siempre reentrena
    python -m src.pipeline --skip-if-trained  # usado por docker compose up
    python -m src.pipeline --reload-data      # recarga el CSV en PostgreSQL

Pasos:
    1. Si no existe el CSV, se avisa (el dataset se genera con src.data.generate).
    2. Si hay base de datos y la tabla está vacía, carga el CSV adentro.
    3. Entrena, compara y guarda los modelos (src.models.train).
"""

import argparse
import sys

import pandas as pd

from src import db
from src.config import MODEL_PATH, ROOT, load_params
from src.models import train


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-if-trained", action="store_true",
                        help="no hace nada si artifacts/model.joblib ya existe")
    parser.add_argument("--reload-data", action="store_true",
                        help="reemplaza la tabla de la base con el CSV crudo")
    args = parser.parse_args()
    params = load_params()

    csv_path = ROOT / params["data"]["raw_path"]
    if not csv_path.exists():
        sys.exit(f"No existe {csv_path}. Generá el dataset con "
                 "`python -m src.data.generate` antes de entrenar.")
    print(f"[1/3] Datos crudos: {csv_path}")

    engine = db.get_engine()
    if engine is None:
        print("[2/3] Sin DATABASE_URL: se entrena directamente desde el CSV")
    elif not db.wait_for_db():
        sys.exit("[2/3] PostgreSQL no responde; abortando.")
    elif args.reload_data or db.count_comentarios(engine) == 0:
        raw = pd.read_csv(csv_path)
        db.replace_comentarios(engine, raw)
        print(f"[2/3] {len(raw)} comentarios cargados en PostgreSQL (tabla comentarios)")
    else:
        print(f"[2/3] PostgreSQL ya tiene {db.count_comentarios(engine)} comentarios")

    if args.skip_if_trained and MODEL_PATH.exists():
        print(f"[3/3] Ya existe {MODEL_PATH}; no se reentrena "
              "(usá 'python -m src.pipeline' para forzarlo)")
        return
    print("[3/3] Entrenando")
    train.main()


if __name__ == "__main__":
    main()
