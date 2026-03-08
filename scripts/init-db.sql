-- LogiSense Database Initialization Script
-- Creates schemas for all modules

-- Module schemas
CREATE SCHEMA IF NOT EXISTS iwms;
COMMENT ON SCHEMA iwms IS 'Intelligent Warehouse Management System';

CREATE SCHEMA IF NOT EXISTS lip;
COMMENT ON SCHEMA lip IS 'Labor Intelligence Platform';

CREATE SCHEMA IF NOT EXISTS ccvp;
COMMENT ON SCHEMA ccvp IS 'Cold Chain Visibility Platform';

CREATE SCHEMA IF NOT EXISTS pise;
COMMENT ON SCHEMA pise IS 'Product & Inventory Slotting Engine';

CREATE SCHEMA IF NOT EXISTS wcvp;
COMMENT ON SCHEMA wcvp IS 'Warehouse Capacity & Visibility Platform';

CREATE SCHEMA IF NOT EXISTS uoih;
COMMENT ON SCHEMA uoih IS 'Unified Operations Intelligence Hub';

-- Platform schemas
CREATE SCHEMA IF NOT EXISTS license;
COMMENT ON SCHEMA license IS 'License management service';

-- Grant usage on all schemas to the application user
DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT unnest(ARRAY['iwms', 'lip', 'ccvp', 'pise', 'wcvp', 'uoih', 'license'])
    LOOP
        EXECUTE format('GRANT ALL PRIVILEGES ON SCHEMA %I TO logisense', schema_name);
    END LOOP;
END $$;

-- Confirm initialization
DO $$
BEGIN
    RAISE NOTICE 'LogiSense database initialized with schemas: iwms, lip, ccvp, pise, wcvp, uoih, license';
END $$;
