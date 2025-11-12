import pandas as pd
import sqlite3

tables = ["TB_BARANG", "stok_opname"]

conn = sqlite3.connect("masterbaru.db")

for t in tables:
    df = pd.read_csv(f"{t}.csv")
    df.to_sql(t, conn, if_exists="replace", index=False)
    print(f"✅ Imported {t} ({len(df)} rows)")

conn.close()
print("✅ Migrasi selesai: masterbaru.db siap dipakai!")
