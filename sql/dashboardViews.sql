-- Views que alimentam o dashboard. Uma view por pagina/visual.
-- Rode depois de createTables.sql e da carga do cleanData.py.

-- ---------------------------------------------------------------------------
-- Dimensao: regime de AIH por condicao (ver METHODOLOGY secao 6)
-- Derivado do dado, nao fixado a mao: o corte e a proporcao de AIHs curtas.
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwDiseaseRegime;
CREATE VIEW vwDiseaseRegime AS
SELECT
    diseaseCode,
    diseaseName,
    SUM(admissions)                                                    AS admissions,
    SUM(shortStayAdmissions)                                           AS shortStay,
    ROUND(100.0 * SUM(shortStayAdmissions) / SUM(admissions), 1)        AS shortStayPct,
    CASE WHEN 1.0 * SUM(shortStayAdmissions) / SUM(admissions) >= 0.5
         THEN 'Tratamento (predominio de dia unico)'
         ELSE 'Internacao clinica' END                                  AS careRegime
FROM hospitalAdmissions
GROUP BY diseaseCode, diseaseName;

-- ---------------------------------------------------------------------------
-- PAGINA 1 - Visao geral
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwOverview;
CREATE VIEW vwOverview AS
SELECT
    a.diseaseCode,
    a.diseaseName,
    r.careRegime,
    SUM(a.admissions)                                                  AS admissions,
    SUM(a.shortStayAdmissions)                                         AS shortStayAdmissions,
    SUM(a.deaths)                                                      AS deaths,
    ROUND(100.0 * SUM(a.deaths) / NULLIF(SUM(a.admissions), 0), 2)     AS inHospitalMortalityPct,
    ROUND(1.0 * SUM(a.hospitalDays) / NULLIF(SUM(a.admissions), 0), 1) AS avgLengthOfStay,
    ROUND(SUM(a.approvedValue), 2)                                     AS approvedValue,
    COUNT(DISTINCT a.ufResidence)                                      AS ufsOfOrigin,
    COUNT(DISTINCT a.municipalityHospital)                             AS municipalitiesTreating,
    COUNT(DISTINCT a.establishmentId)                                  AS establishments
FROM hospitalAdmissions a
JOIN vwDiseaseRegime r ON r.diseaseCode = a.diseaseCode
GROUP BY a.diseaseCode, a.diseaseName, r.careRegime;

-- ---------------------------------------------------------------------------
-- PAGINA 1/2 - serie mensal
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwMonthly;
CREATE VIEW vwMonthly AS
SELECT
    a.year,
    a.month,
    printf('%04d-%02d', a.year, a.month) AS yearMonth,
    a.diseaseCode,
    a.diseaseName,
    r.careRegime,
    SUM(a.admissions)          AS admissions,
    SUM(a.shortStayAdmissions) AS shortStayAdmissions,
    SUM(a.deaths)              AS deaths
FROM hospitalAdmissions a
JOIN vwDiseaseRegime r ON r.diseaseCode = a.diseaseCode
GROUP BY a.year, a.month, a.diseaseCode, a.diseaseName, r.careRegime;

-- ---------------------------------------------------------------------------
-- PAGINA 2/3 - por UF de residencia, ja normalizado pela cobertura
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwByUf;
CREATE VIEW vwByUf AS
SELECT
    a.ufResidence                                                      AS uf,
    a.diseaseCode,
    a.diseaseName,
    r.careRegime,
    SUM(a.admissions)                                                  AS admissions,
    SUM(a.deaths)                                                      AS deaths,
    ROUND(1.0 * SUM(a.hospitalDays) / NULLIF(SUM(a.admissions), 0), 1) AS avgLengthOfStay,
    ROUND(SUM(a.approvedValue), 2)                                     AS approvedValue,
    c.monthsAvailable,
    c.coverageRatio,
    -- Projecao para 12 meses. AM e PI tem 11 meses; sem isso apareceriam
    -- com demanda artificialmente menor que as vizinhas.
    ROUND(SUM(a.admissions) / NULLIF(c.coverageRatio, 0), 1)           AS admissionsAnnualized
FROM hospitalAdmissions a
JOIN vwDiseaseRegime r ON r.diseaseCode = a.diseaseCode
LEFT JOIN dataCoverage c ON c.uf = a.ufResidence AND c.year = a.year
GROUP BY a.ufResidence, a.diseaseCode, a.diseaseName, r.careRegime,
         c.monthsAvailable, c.coverageRatio;

-- ---------------------------------------------------------------------------
-- PAGINA 4 - concentracao territorial (o achado central)
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwConcentration;
CREATE VIEW vwConcentration AS
WITH porMunicipio AS (
    SELECT diseaseCode, diseaseName, municipalityHospital,
           SUM(admissions) AS admissions
    FROM hospitalAdmissions
    GROUP BY diseaseCode, diseaseName, municipalityHospital
),
ranqueado AS (
    SELECT p.*,
           ROW_NUMBER() OVER (PARTITION BY diseaseCode
                              ORDER BY admissions DESC) AS rankInDisease,
           SUM(admissions) OVER (PARTITION BY diseaseCode) AS diseaseTotal
    FROM porMunicipio p
)
SELECT
    diseaseCode, diseaseName, municipalityHospital, admissions,
    rankInDisease,
    ROUND(100.0 * admissions / diseaseTotal, 2) AS pctOfDisease,
    ROUND(100.0 * SUM(admissions) OVER (PARTITION BY diseaseCode
                                        ORDER BY admissions DESC
                                        ROWS UNBOUNDED PRECEDING)
          / diseaseTotal, 2)                    AS cumulativePct
FROM ranqueado;

-- ---------------------------------------------------------------------------
-- PAGINA 4 - fluxo municipal (origem -> destino)
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwFlow;
CREATE VIEW vwFlow AS
SELECT
    a.diseaseCode,
    a.diseaseName,
    a.municipalityResidence AS originMunicipality,
    a.ufResidence           AS originUf,
    a.municipalityHospital  AS destMunicipality,
    a.ufHospital            AS destUf,
    CASE WHEN a.municipalityResidence = a.municipalityHospital THEN 'Mesmo municipio'
         WHEN a.ufResidence = a.ufHospital                     THEN 'Outro municipio, mesma UF'
         ELSE 'Outra UF' END AS travelType,
    SUM(a.admissions)        AS admissions
FROM hospitalAdmissions a
GROUP BY a.diseaseCode, a.diseaseName,
         a.municipalityResidence, a.ufResidence,
         a.municipalityHospital, a.ufHospital, travelType;

-- ---------------------------------------------------------------------------
-- PAGINA 4 - resumo do deslocamento
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS vwTravelSummary;
CREATE VIEW vwTravelSummary AS
SELECT
    diseaseCode, diseaseName, travelType,
    SUM(admissions) AS admissions,
    ROUND(100.0 * SUM(admissions)
          / SUM(SUM(admissions)) OVER (PARTITION BY diseaseCode), 1) AS pct
FROM vwFlow
GROUP BY diseaseCode, diseaseName, travelType;
