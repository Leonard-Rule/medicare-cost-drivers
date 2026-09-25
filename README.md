# Medicare Cost Drivers: Standardized Service-Category Spending on CMS Synthetic Claims

Portfolio project for Leo Rule. It applies the published **Peterson-Milbank consensus cost-driver
specifications** to CMS's public **synthetic Medicare FFS claims**. The goal is to show claims methodology end to
end: service-category mapping, member months, PMPM trends, primary care share of spend, and a Part D view of the
drugs selected for Medicare price negotiation.

> Built only from public specifications and public synthetic data. No employer code, logic, or data.

## Data
- **CMS Synthetic Medicare Enrollment, FFS Claims, and PDE** (data.cms.gov, 2023 release): 8,671 synthetic
  beneficiaries, enrollment 2015–2025, pipe-delimited. Files: beneficiary, inpatient, outpatient, carrier,
  SNF, HHA, hospice, DME, PDE. The user guide is in `docs/`.
- Specs: the Peterson-Milbank *Consensus Administrative Specifications for Health Care Cost Driver Analyses*
  (service categories, primary care, retail and medical pharmacy) and the *Cost Growth Target* specs, June 2025.
  Download links are in `docs/SOURCES.md`. They aren't redistributed here.
- The full dataset is included, gzipped in `data/raw/*.csv.gz` (~60 MB; ~1.2 GB uncompressed). DuckDB reads the
  .gz files directly, so there's no unzip step. Original source URLs are in `docs/SOURCES.md`.

## Setup
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python src/build_db.py          # loads data/raw/*.csv.gz -> data/cost_drivers.duckdb
```

## Plan (one week)
| Step | Output | Spec section |
|---|---|---|
| 1. Member months | Part A+B FFS months per bene-year (HI/SMI months minus HMO months) | CGT specs, denominators |
| 2. Topline service categories | Every claim line assigned to 1 of 6 categories | "Defining Service Categories", p. 5–7 |
| 3. PMPM by category × year | Table + trend chart | Cost-driver analyses |
| 4. Primary care spend | Primary care $ and % of total (provider type, POS, HCPCS/CPT lists) | "Primary Care Claims Spending", Steps 1–6 |
| 5. Pharmacy | Retail (PDE) vs. medical pharmacy (J-codes on outpatient/carrier lines) | Retail and Medical Pharmacy specs |
| 6. Part D negotiated drugs | Spend on the 2026 Maximum Fair Price drugs (NDC match) | Extension, mirrors real-world MFP savings work |
| 7. Validation + write-up | Reconciliation checks, 1-page methods memo, 2–3 charts | — |

### Draft mapping: Medicare FFS file → Milbank topline category
Verify each line against the spec before using it.
- **Inpatient Hospital**: `inpatient` claims, bill type 11x/41x (Medicare CLM_FAC_TYPE_CD=1 + CLM_SRVC_CLSFCTN_TYPE_CD=1)
- **Outpatient Hospital**: `outpatient` claims, bill type 13x/85x (CAH), incl. ER and observation, **minus
  medical-pharmacy lines** if they're broken out
- **Professional**: `carrier` lines (CMS-1500); use POS/specialty for subcategories
- **Long-Term Care**: `snf` (and HHA? The spec lists HCBS under LTC; decide and document it)
- **Retail Pharmacy**: `pde`, TOT_RX_CST_AMT or plan paid (pick one allowed-amount proxy and document it)
- **Other**: `dme`, `hospice`, `hha` (if not LTC), anything left over
- Dollars: Medicare paid (`CLM_PMT_AMT`, line `LINE_NCH_PMT_AMT` / `REV_CNTR_PMT_AMT_AMT`). The specs use
  **allowed** amounts. Approximate allowed = paid + beneficiary cost share + primary payer paid, and document that.

## First findings (smoke test, `sql/00_smoke_test.sql`)
- The load works: 1.12M carrier lines, 575K outpatient lines, 58K inpatient, 516K PDE; ~75K–104K FFS member months per year.
- **Data-quality flag:** outpatient comes to ~$940–1,130 PMPM, far above real Medicare FFS (~$150–250). Total
  synthetic spend isn't realistic in scale. Treat results as a **methods demonstration**, not real-world
  benchmarks, and say so in the write-up. Check whether outpatient headers repeat or line amounts are inflated.
- DME is almost empty (~$0.28 PMPM), so the synthetic DME file is sparse.

## Layout
```
data/raw/        source files, gzipped (.csv.gz)
data/*.duckdb    local database (gitignored)
docs/            specs, CMS user guide, sources
sql/             analysis queries, numbered by step
src/             Python: load, build tables, charts
```
