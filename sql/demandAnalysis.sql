-- ---------------------------------------------------------------------------
-- 1. Demanda: AIHs por UF de residencia e doenca
-- ---------------------------------------------------------------------------
SELECT
    ufResidence,
    diseaseName,
    SUM(admissions)                                   AS totalAdmissions,
    SUM(deaths)                                       AS totalDeaths,
    ROUND(1.0 * SUM(deaths) / NULLIF(SUM(admissions), 0) * 100, 2) AS inHospitalMortalityPct,
    ROUND(1.0 * SUM(hospitalDays) / NULLIF(SUM(admissions), 0), 1) AS avgLengthOfStay,
    ROUND(SUM(approvedValue), 2)                      AS approvedValue
FROM hospitalAdmissions
GROUP BY ufResidence, diseaseName
ORDER BY totalAdmissions DESC;

-- ---------------------------------------------------------------------------
-- 2. Evolucao temporal por doenca
-- ---------------------------------------------------------------------------
SELECT
    year,
    diseaseName,
    SUM(admissions) AS totalAdmissions
FROM hospitalAdmissions
GROUP BY year, diseaseName
ORDER BY year, diseaseName;

-- ---------------------------------------------------------------------------
-- 3. Demanda por 100 mil habitantes (residencia)
-- ---------------------------------------------------------------------------
SELECT
    a.year,
    a.ufResidence                                              AS uf,
    SUM(a.admissions)                                          AS totalAdmissions,
    p.population,
    ROUND(1.0 * SUM(a.admissions) / p.population * 100000, 2)   AS admissionsPer100k
FROM hospitalAdmissions a
JOIN population p
  ON p.uf = a.ufResidence AND p.year = a.year
GROUP BY a.year, a.ufResidence, p.population
ORDER BY admissionsPer100k DESC;

-- ---------------------------------------------------------------------------
-- 4. Fluxo interestadual: residencia -> internacao (alimenta o Sankey)
-- ---------------------------------------------------------------------------
SELECT
    ufResidence,
    ufHospital,
    SUM(admissions) AS totalAdmissions
FROM hospitalAdmissions
WHERE ufResidence IS NOT NULL
  AND ufHospital  IS NOT NULL
  AND ufResidence <> ufHospital
GROUP BY ufResidence, ufHospital
HAVING SUM(admissions) > 0
ORDER BY totalAdmissions DESC;

-- ---------------------------------------------------------------------------
-- 5. Taxa de evasao: quanto de cada UF e atendido fora dela
-- ---------------------------------------------------------------------------
SELECT
    ufResidence,
    SUM(admissions)                                                          AS totalAdmissions,
    SUM(CASE WHEN ufHospital <> ufResidence THEN admissions ELSE 0 END)      AS outOfStateAdmissions,
    ROUND(1.0 * SUM(CASE WHEN ufHospital <> ufResidence THEN admissions ELSE 0 END)
          / NULLIF(SUM(admissions), 0) * 100, 2)                             AS outOfStatePct
FROM hospitalAdmissions
WHERE ufResidence IS NOT NULL AND ufHospital IS NOT NULL
GROUP BY ufResidence
ORDER BY outOfStatePct DESC;
