"""Load the CMS synthetic RIF files (pipe-delimited, gzipped in data/raw) into a local DuckDB file.
DuckDB reads .csv.gz directly; cost_drivers.duckdb is gitignored."""
import duckdb, glob, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
con = duckdb.connect(str(ROOT / "data" / "cost_drivers.duckdb"))
opts = "delim='|', header=true, all_varchar=true, ignore_errors=false"
con.execute(f"CREATE OR REPLACE TABLE beneficiary AS SELECT * FROM read_csv('{RAW}/beneficiary_20*.csv.gz', {opts}, union_by_name=true)")
for t in ["inpatient", "outpatient", "carrier", "snf", "hha", "hospice", "dme", "pde"]:
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_csv('{RAW}/{t}.csv.gz', {opts})")
for (t,) in con.execute("SELECT table_name FROM information_schema.tables ORDER BY 1").fetchall():
    print(f"{t:12s} {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:>10,}")
