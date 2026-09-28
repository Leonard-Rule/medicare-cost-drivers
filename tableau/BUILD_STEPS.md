# Building the Tableau dashboard by hand

Use `Medicare Cost Drivers (data only).twbx` if the full workbook won't open. It has the data and every
calculated field already defined, so you only build the views. It takes about 20 minutes.

**Check your numbers against:** 2022 total PMPM $1,987 · 2022 inpatient $341.49 · 2022 primary care share 1.73%.

## Calculated fields (already in the file)
| Field | Formula | Why |
|---|---|---|
| Member Months A+B FFS | `{FIXED [Year] : SUM([A+B FFS Member Months (row)])}` | Member months are on their own rows, so this puts the year's total on every row |
| Member Months Part D | `{FIXED [Year] : SUM([Part D Member Months (row)])}` | Same thing for the pharmacy denominator |
| PMPM Denominator | Part D months if Retail Pharmacy, else A+B months | Pharmacy is per Part D member |
| PMPM | `SUM([Allowed $]) / MIN([PMPM Denominator])` | |
| Total PMPM | medical $ ÷ A+B months + pharmacy $ ÷ Part D months | |
| Primary Care % of Medical Spend | primary care $ ÷ non-pharmacy spend $ | |
| Primary Care PMPM | primary care $ ÷ A+B months | |

## Filters on every sheet
Drag **Medicaid (Dual) Status**, **Age Band** and **Sex** to Filters (select all), then right-click each →
**Add to Context** (the pill turns grey). FIXED is calculated before normal filters, so without context
the dollars would filter but the member months wouldn't. Right-click each → **Show Filter**.

## Sheet 1: PMPM by Category
1. Filters: **Row Type** = `spend`.
2. Columns: **Year** (discrete). Rows: **PMPM**.
3. Marks: Bar. Color: **Service Category**. Label: optional.

## Sheet 2: Total PMPM Trend
1. Columns: **Year**. Rows: **Total PMPM** (no Row Type filter; it needs all rows).
2. Marks: Line. Label: on.

## Sheet 3: Subcategory PMPM
1. Filters: **Row Type** = `spend`, **Year** = 2022.
2. Rows: **Service Category**, **Subcategory**. Columns: **PMPM**.
3. Color: **Service Category**. Sort descending within category. Label: on.

## Sheet 4: Primary Care Share
1. Columns: **Year**. Rows: **Primary Care % of Medical Spend** (no Row Type filter).
2. Marks: Bar. Label: on. Format as percentage, 2 decimals.

## Dashboard
1. New Dashboard, size 1400 × 900 (or Automatic).
2. Filter cards across the top, then Sheet 1 and 2 in the top row and Sheet 3 and 4 in the bottom row.
3. On each filter card: ▾ → **Apply to Worksheets → All Using This Data Source**.
4. Colors to match the D3 dashboard: Inpatient #2a78d6, Outpatient #eb6834, Professional #1baf7a,
   Long-Term Care #eda100, Retail Pharmacy #e87ba4, Other #008300.
5. **File → Save to Tableau Public As…** to publish.
