-- NeonDB Schema for HAW Module Recognition System
-- Run this in NeonDB SQL Editor after creating your project

-- Personen (Professors/Staff)
CREATE TABLE personen (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Module
CREATE TABLE module (
  id SERIAL PRIMARY KEY,
  module_id VARCHAR(50) NOT NULL UNIQUE,
  title TEXT NOT NULL,
  credits INTEGER,
  sws INTEGER,
  semester INTEGER,
  lernziele TEXT,
  pruefungsleistung TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Units
CREATE TABLE units (
  id SERIAL PRIMARY KEY,
  unit_id VARCHAR(50) NOT NULL UNIQUE,
  title TEXT NOT NULL,
  module_id INTEGER REFERENCES module(id) ON DELETE CASCADE,
  semester INTEGER,
  sws INTEGER,
  workload VARCHAR(50),
  lehrsprache VARCHAR(50),
  lernziele TEXT,
  inhalte TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Many-to-many: Units ↔ Personen
CREATE TABLE units_personen (
  unit_id INTEGER REFERENCES units(id) ON DELETE CASCADE,
  person_id INTEGER REFERENCES personen(id) ON DELETE CASCADE,
  PRIMARY KEY (unit_id, person_id)
);

-- Indexes for performance
CREATE INDEX idx_units_module_id ON units(module_id);
CREATE INDEX idx_units_unit_id ON units(unit_id);
CREATE INDEX idx_module_module_id ON module(module_id);

-- Update timestamp triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_personen_updated_at BEFORE UPDATE ON personen
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_module_updated_at BEFORE UPDATE ON module
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_units_updated_at BEFORE UPDATE ON units
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
