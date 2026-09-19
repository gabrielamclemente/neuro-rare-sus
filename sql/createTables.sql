-- Modelo de dados do NeuroRare SUS (SQLite / Postgres).
-- Granularidade do fato: ano x mes x UF residencia x UF internacao x doenca.
-- Nao existe paciente unico: o SIH registra PRODUCAO (AIHs), nao pessoas.

DROP TABLE IF EXISTS hospitalAdmissions;
CREATE TABLE hospitalAdmissions (
    id                    INTEGER PRIMARY KEY,
    year                  INTEGER NOT NULL,
    month                 INTEGER NOT NULL,
    ufResidence           TEXT,
    ufHospital            TEXT,
    municipalityResidence TEXT,
    municipalityHospital  TEXT,
    establishmentId       TEXT,          -- CNES
    diseaseCode           TEXT NOT NULL, -- G120, G122, G35, G700, E851
    diseaseName           TEXT NOT NULL,
    admissions            INTEGER NOT NULL DEFAULT 0,
    deaths                INTEGER NOT NULL DEFAULT 0,
    hospitalDays          INTEGER NOT NULL DEFAULT 0,
    approvedValue         REAL    NOT NULL DEFAULT 0
);

DROP TABLE IF EXISTS rareDiseaseServices;
CREATE TABLE rareDiseaseServices (
    establishmentId          TEXT PRIMARY KEY,   -- CNES
    establishmentName        TEXT,
    uf                       TEXT NOT NULL,
    municipality             TEXT,
    serviceType              TEXT,               -- referencia / atencao especializada / terapia genica
    specializedDiseaseService INTEGER NOT NULL DEFAULT 0
);

DROP TABLE IF EXISTS population;
CREATE TABLE population (
    year       INTEGER NOT NULL,
    uf         TEXT    NOT NULL,
    population INTEGER NOT NULL,
    PRIMARY KEY (year, uf)
);

CREATE INDEX idxAdmUfDisease ON hospitalAdmissions (ufResidence, diseaseCode);
CREATE INDEX idxAdmYear      ON hospitalAdmissions (year, month);
CREATE INDEX idxAdmCnes      ON hospitalAdmissions (establishmentId);
