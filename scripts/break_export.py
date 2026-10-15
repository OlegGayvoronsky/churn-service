"""Испорченная выгрузка для проверки шага validate: увеличение доли уходящих пользователей,
   так как в источнике из-за ошибки поменялись метки - теперь за положительный класс считаются те,
   кто остаются.

  uv run python scripts/break_export.py

Перезаписывает data/train.csv, ни одной ошибки при этом не возникает: файл читается,
типы те же, строк столько же. Ловит такое только проверка значений и распределения.
Вернуть как было: git checkout -- data/train.csv.dvc && uv run dvc checkout
"""
from pathlib import Path

import pandas as pd

PATH = Path("data/train.csv")
df = pd.read_csv(PATH)
df["Exited"] = 1.0 * (df["Exited"] == 0)
df.to_parquet(PATH, index=False)
print(f"{PATH}: новые метки, доля классов {df['Exited'].mean():.2f}, строк {len(df)}")