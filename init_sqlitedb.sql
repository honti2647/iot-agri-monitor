-- Adatbázis inicializáló script
-- Csak a 'measure' tábla és az indexek

-- A méréseket tartalmazó fő tábla
CREATE TABLE IF NOT EXISTS measure (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    date DATETIME NOT NULL,           -- Időbélyeg (érdemes kötelezővé tenni)
    temperature REAL,                 -- Hőmérséklet
    humidity REAL,                    -- Páratartalom
    vpd REAL,                         -- Vapor Pressure Deficit (Gőznyomás-hiány)
    soil_an_1_raw REAL,               -- Analóg talajszenzor nyers érték
    soil_an_1_volt REAL,              -- Analóg talajszenzor feszültség
    soil_an_1_pct REAL,               -- Analóg talajszenzor százalékos érték
    seesaw1_raw REAL,                 -- Adafruit Seesaw (kapacitív) nyers érték
    seesaw1_pct REAL,                 -- Seesaw százalékos nedvesség
    seesaw1_temp REAL,                -- Seesaw saját hőmérséklet szenzora
    synced INTEGER DEFAULT 0          -- Szinkronizációs flag (0: nem, 1: igen)
);

-- Index a dátumra a gyorsabb lekérdezések és grafikonok miatt
CREATE INDEX IF NOT EXISTS dateindex ON measure (date);
