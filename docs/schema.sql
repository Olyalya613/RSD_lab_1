-- gen_random_uuid() is built into PostgreSQL 16; no extension privilege needed.
CREATE TABLE IF NOT EXISTS travel_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 title VARCHAR(200) NOT NULL CHECK (length(trim(title)) > 0),
 description TEXT, start_date DATE, end_date DATE,
 budget NUMERIC(10,2) CHECK (budget >= 0),
 currency VARCHAR(3) NOT NULL DEFAULT 'USD' CHECK (currency ~ '^[A-Z]{3}$'),
 is_public BOOLEAN NOT NULL DEFAULT false,
 order_version INTEGER NOT NULL DEFAULT 1 CHECK (order_version > 0),
 version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE TABLE IF NOT EXISTS locations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 travel_plan_id UUID NOT NULL REFERENCES travel_plans(id) ON DELETE CASCADE,
 name VARCHAR(200) NOT NULL CHECK (length(trim(name)) > 0), address TEXT,
 latitude NUMERIC(10,6) CHECK (latitude BETWEEN -90 AND 90),
 longitude NUMERIC(11,6) CHECK (longitude BETWEEN -180 AND 180),
 visit_order INTEGER NOT NULL CHECK (visit_order > 0),
 arrival_date TIMESTAMPTZ, departure_date TIMESTAMPTZ,
 budget NUMERIC(10,2) CHECK (budget >= 0), notes TEXT,
 version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (departure_date IS NULL OR arrival_date IS NULL OR departure_date >= arrival_date),
 CONSTRAINT unique_plan_order UNIQUE (travel_plan_id, visit_order) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS idx_plans_updated ON travel_plans(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_locations_plan_order ON locations(travel_plan_id, visit_order);
CREATE OR REPLACE FUNCTION touch_plan() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS touch_plan_trigger ON travel_plans;
CREATE TRIGGER touch_plan_trigger BEFORE UPDATE ON travel_plans FOR EACH ROW EXECUTE FUNCTION touch_plan();

-- Idempotent migration for an existing Lab 1 database.
ALTER TABLE travel_plans ADD COLUMN IF NOT EXISTS order_version INTEGER NOT NULL DEFAULT 1 CHECK (order_version > 0);
