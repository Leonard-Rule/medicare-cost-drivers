-- Sanity check: Medicare FFS member months (Part A+B) and paid dollars by claim file and year.
-- Carrier/outpatient/etc. are line-level (header repeated per line), so dedupe to CLM_ID first.
WITH mm AS (
  SELECT BENE_ENROLLMT_REF_YR AS yr,
         SUM(LEAST(TRY_CAST(BENE_HI_CVRAGE_TOT_MONS AS INT), TRY_CAST(BENE_SMI_CVRAGE_TOT_MONS AS INT))
             - COALESCE(TRY_CAST(BENE_HMO_CVRAGE_TOT_MONS AS INT), 0)) AS ab_ffs_member_months
  FROM beneficiary GROUP BY 1),
hdr AS (
  SELECT 'inpatient' f, CLM_ID, any_value(CLM_THRU_DT) dt, any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) paid FROM inpatient GROUP BY CLM_ID
  UNION ALL SELECT 'outpatient', CLM_ID, any_value(CLM_THRU_DT), any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) FROM outpatient GROUP BY CLM_ID
  UNION ALL SELECT 'carrier',    CLM_ID, any_value(CLM_THRU_DT), any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) FROM carrier GROUP BY CLM_ID
  UNION ALL SELECT 'snf',        CLM_ID, any_value(CLM_THRU_DT), any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) FROM snf GROUP BY CLM_ID
  UNION ALL SELECT 'hha',        CLM_ID, any_value(CLM_THRU_DT), any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) FROM hha GROUP BY CLM_ID
  UNION ALL SELECT 'hospice',    CLM_ID, any_value(CLM_THRU_DT), any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) FROM hospice GROUP BY CLM_ID
  UNION ALL SELECT 'dme',        CLM_ID, any_value(CLM_THRU_DT), any_value(TRY_CAST(CLM_PMT_AMT AS DOUBLE)) FROM dme GROUP BY CLM_ID),
paid AS (SELECT substr(dt, -4) yr, f, SUM(paid) paid FROM hdr GROUP BY 1, 2)
SELECT p.yr, p.f, round(p.paid) paid, mm.ab_ffs_member_months, round(p.paid / NULLIF(mm.ab_ffs_member_months, 0), 2) pmpm
FROM paid p LEFT JOIN mm ON mm.yr = p.yr
WHERE p.yr BETWEEN '2016' AND '2022' ORDER BY p.yr, p.f;
