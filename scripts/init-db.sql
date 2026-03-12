-- Create non-superuser app role
CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';

-- Grant DB access
GRANT CONNECT ON DATABASE timeseries_db TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- DML only no DDL (CREATE/ALTER/DROP handled by postgres migration user)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;
