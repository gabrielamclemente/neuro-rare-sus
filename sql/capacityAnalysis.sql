-- ---------------------------------------------------------------------------
-- 1. Oferta: servicos habilitados em doencas raras por UF
-- ---------------------------------------------------------------------------
SELECT
    uf,
    COUNT(*)                                                          AS specializedServices,
    SUM(CASE WHEN serviceType LIKE '%referencia%'     THEN 1 ELSE 0 END) AS referenceServices,
    SUM(CASE WHEN serviceType LIKE '%terapia genica%' THEN 1 ELSE 0 END) AS geneTherapyServices
FROM rareDiseaseServices
WHERE specializedDiseaseService = 1
GROUP BY uf
ORDER BY specializedServices DESC;

-- ---------------------------------------------------------------------------
-- 2. Demanda x capacidade (coracao da pagina 3 do Power BI)
--
-- IMPORTANTE: admissionsPerService e um INDICADOR EXPLORATORIO da relacao
-- entre demanda hospitalar registrada e oferta especializada. Nao mede acesso
-- real: nem toda internacao exige centro especializado, e um servico habilitado
-- atende pacientes de varias UFs (ver query 5 de demandAnalysis.sql).
-- LEFT JOIN de proposito: UF sem nenhum servico e o achado mais interessante.
-- ---------------------------------------------------------------------------
WITH demand AS (
    SELECT ufResidence AS uf, SUM(admissions) AS totalAdmissions
    FROM hospitalAdmissions
    WHERE ufResidence IS NOT NULL
    GROUP BY ufResidence
),
capacity AS (
    SELECT uf, COUNT(*) AS specializedServices
    FROM rareDiseaseServices
    WHERE specializedDiseaseService = 1
    GROUP BY uf
)
SELECT
    d.uf,
    d.totalAdmissions,
    COALESCE(c.specializedServices, 0) AS specializedServices,
    CASE
        WHEN COALESCE(c.specializedServices, 0) = 0 THEN NULL
        ELSE ROUND(1.0 * d.totalAdmissions / c.specializedServices, 1)
    END AS admissionsPerService,
    CASE WHEN COALESCE(c.specializedServices, 0) = 0
         THEN 'sem servico habilitado' ELSE '' END AS flag
FROM demand d
LEFT JOIN capacity c ON c.uf = d.uf
ORDER BY d.totalAdmissions DESC;

-- ---------------------------------------------------------------------------
-- 3. Concentracao: UFs que atendem residentes de outros estados
-- ---------------------------------------------------------------------------
SELECT
    a.ufHospital                                                        AS uf,
    COALESCE(c.specializedServices, 0)                                  AS specializedServices,
    SUM(a.admissions)                                                   AS admissionsPerformed,
    SUM(CASE WHEN a.ufResidence <> a.ufHospital THEN a.admissions ELSE 0 END) AS fromOtherStates,
    ROUND(1.0 * SUM(CASE WHEN a.ufResidence <> a.ufHospital THEN a.admissions ELSE 0 END)
          / NULLIF(SUM(a.admissions), 0) * 100, 2)                      AS inboundPct
FROM hospitalAdmissions a
LEFT JOIN (
    SELECT uf, COUNT(*) AS specializedServices
    FROM rareDiseaseServices WHERE specializedDiseaseService = 1 GROUP BY uf
) c ON c.uf = a.ufHospital
WHERE a.ufHospital IS NOT NULL AND a.ufResidence IS NOT NULL
GROUP BY a.ufHospital, c.specializedServices
ORDER BY inboundPct DESC;
