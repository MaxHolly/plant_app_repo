DROP TABLE IF EXISTS User;
DROP TABLE IF EXISTS Plant;
DROP TABLE IF EXISTS UserPlant;

-- User Schema
CREATE TABLE IF NOT EXISTS User (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    avatar TEXT NOT NULL,
    password TEXT NOT NULL,
    user_description TEXT,
    last_time_seen TIMESTAMP
);

-- Plant Schema
CREATE TABLE IF NOT EXISTS Plant (
    plant_id INTEGER PRIMARY KEY,
    botanical_name TEXT,
    common_name TEXT,
    plant_type TEXT,
    water_needs TEXT,
    min_water_consumption INT,
    max_water_consumption INT,
    climate_zones TEXT,
    light_needs TEXT,
    soil_type TEXT,
    maintenance TEXT,
    flower_color TEXT,
    foliage_color TEXT,
    perfume TEXT,
    aromatic TEXT,
    edible TEXT,
    bore_water_tolerance TEXT,
    frost_tolerance TEXT,
    image_location TEXT
);

-- UserPlant Schema (Many-to-Many Relationship)
CREATE TABLE IF NOT EXISTS  UserPlant (
    user_plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plant_id INTEGER,
    size REAL,
    sun_exposure TEXT,
    last_watered DATETIME,
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (plant_id) REFERENCES Plant(plant_id)
);
