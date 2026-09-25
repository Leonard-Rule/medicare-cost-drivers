"""Run the analysis end to end: sql/01..06 in order, then export results to output/.
Needs data/cost_drivers.duckdb from src/build_db.py (it's built automatically if missing).
The output/*.csv files feed the README charts, the D3 dashboard and the Tableau workbook."""
import duckdb, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DB, OUT = ROOT / "data" / "cost_drivers.duckdb", ROOT / "output"

if not DB.exists():
    subprocess.run([sys.executable, str(ROOT / "src" / "build_db.py")], check=True)
con = duckdb.connect(str(DB))
con.execute("SET enable_progress_bar = false")

# Reference code lists (Milbank primary care appendices)
for t in ["pc_service_codes", "pc_place_of_service", "pc_medicare_specialty"]:
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_csv('{ROOT}/ref/{t}.csv', all_varchar=true)")

for f in sorted((ROOT / "sql").glob("0[1-9]_*.sql")):
    print(f"running {f.name}")
    con.execute(f.read_text())

OUT.mkdir(exist_ok=True)
exports = {
    "member_months_by_year": "SELECT * FROM member_months_by_year WHERE study_yr(yr)",
    "pmpm_by_category": "SELECT * FROM pmpm_by_category ORDER BY yr, service_category",
    "pmpm_total": "SELECT * FROM pmpm_total",
    "pmpm_growth": "SELECT * FROM pmpm_growth ORDER BY service_category, yr",
    "primary_care_by_year": "SELECT * FROM primary_care_by_year",
    "primary_care_by_service": "SELECT * FROM primary_care_by_service",
    "spend_fact": "SELECT * FROM spend_fact ORDER BY ALL",
    "mm_fact": "SELECT * FROM mm_fact ORDER BY ALL",
    "pc_fact": "SELECT * FROM pc_fact ORDER BY ALL",
    "validation": "SELECT * FROM validation",
}
# One flat table for Tableau: spend, member-month and primary care rows stacked (row_type says which).
# Tableau computes PMPM with {FIXED [yr] : SUM([ab_mm])}, so its demographic filters must be context filters.
def labeled(t):
    return f"SELECT CASE WHEN dual THEN 'Dual' ELSE 'Non-dual' END AS dual_status, * EXCLUDE (dual) FROM {t}"
exports["tableau_data"] = f"""
    SELECT 'spend' AS row_type, yr, service_category, subcategory, type_of_service, NULL AS service_group,
           dual_status, age_band, sex, round(allowed, 2) AS allowed, NULL AS pc_allowed, NULL AS ab_mm, NULL AS pd_mm
    FROM ({labeled('spend_fact')})
    UNION ALL
    SELECT 'member_months', yr, NULL, NULL, NULL, NULL, dual_status, age_band, sex, NULL, NULL, ab_ffs_mm, partd_mm
    FROM ({labeled('mm_fact')})
    UNION ALL
    SELECT 'primary_care', yr, NULL, NULL, NULL, service_group, dual_status, age_band, sex, NULL, round(allowed, 2), NULL, NULL
    FROM ({labeled('pc_fact')})
    ORDER BY 1, 2"""
for name, q in exports.items():
    con.execute(f"COPY ({q}) TO '{OUT}/{name}.csv' (HEADER)")

# Dashboard data: same facts as the CSVs, bundled as one JS file so dashboard/index.html opens
# straight from disk (no web server needed)
import json
def rows(q):
    cur = con.execute(q); cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]
data = {
    "spend": rows("""SELECT yr, service_category AS cat, subcategory AS sub, dual, age_band AS age, sex,
                            round(sum(allowed), 2) AS allowed FROM spend_fact GROUP BY ALL ORDER BY ALL"""),
    "mm": rows("SELECT yr, dual, age_band AS age, sex, ab_ffs_mm AS ab, partd_mm AS pd FROM mm_fact ORDER BY ALL"),
    "pc": rows("""SELECT yr, service_group AS grp, dual, age_band AS age, sex, round(allowed, 2) AS allowed,
                         services FROM pc_fact ORDER BY ALL"""),
    "validation": rows("SELECT check_name, expected, actual, status, note FROM validation"),
}
(ROOT / "dashboard").mkdir(exist_ok=True)
(ROOT / "dashboard" / "data.js").write_text("window.DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")

print("\nvalidation")
for id_, check, exp, act, status, _ in con.execute("SELECT * FROM validation").fetchall():
    print(f"  {status:4s}  {check:60s} expected {exp:>14s}  got {act}")
if con.execute("SELECT count(*) FROM validation WHERE status = 'FAIL'").fetchone()[0]:
    sys.exit("validation failed")
print("\n", con.sql("SELECT * FROM pmpm_total"))
