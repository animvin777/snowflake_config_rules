-- This is the setup script that runs while installing a Snowflake Native App in a consumer account.
-- Snowflake Config Rules - Monitors warehouse compliance with configurable rules

-- Create versioned schema to hold the code
CREATE OR ALTER VERSIONED SCHEMA core;

-- Create application role for managing the app
CREATE APPLICATION ROLE IF NOT EXISTS config_rules_admin;

-- Create schema to hold data with 0 days retention
CREATE SCHEMA IF NOT EXISTS data_schema 
  DATA_RETENTION_TIME_IN_DAYS = 0;


-- Create table to store warehouse details
CREATE TABLE IF NOT EXISTS data_schema.warehouse_details (
    name VARCHAR(255),
    type VARCHAR(50),
    size VARCHAR(50),
    min_cluster_count NUMBER,
    max_cluster_count NUMBER,
    max_concurrency_level NUMBER,
    statement_queued_timeout_in_seconds NUMBER,
    statement_timeout_in_seconds NUMBER,
    auto_suspend NUMBER,
    created_on TIMESTAMP_LTZ,
    resumed_on TIMESTAMP_LTZ,
    updated_on TIMESTAMP_LTZ,
    owner VARCHAR(255),
    scaling_policy VARCHAR(50),
    comment VARCHAR(500),
    capture_timestamp TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);


-- Create table to store database, schema, and table retention details
CREATE TABLE IF NOT EXISTS data_schema.database_retention_details (
    object_type VARCHAR(50) NOT NULL,  -- 'DATABASE', 'SCHEMA', 'TABLE'
    database_name VARCHAR(255),
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    table_type VARCHAR(50),
    data_retention_time_in_days NUMBER,
    owner VARCHAR(255),
    created_on TIMESTAMP_LTZ,
    last_altered TIMESTAMP_LTZ,
    row_count NUMBER,
    bytes NUMBER,
    comment VARCHAR(500),
    capture_timestamp TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);


-- Create table to store configuration rules
CREATE TABLE IF NOT EXISTS data_schema.config_rules (
    rule_id VARCHAR(100) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    rule_description VARCHAR(500),
    rule_type VARCHAR(50) NOT NULL,  -- 'Warehouse', 'Database'
    check_parameter VARCHAR(100) NOT NULL,
    comparison_operator VARCHAR(10) NOT NULL,  -- 'MAX', 'MIN', 'EQUALS', 'NOT_EQUALS'
    unit VARCHAR(50),  -- 'seconds', 'minutes', etc.
    default_threshold NUMBER,  -- Default threshold value for the rule
    allow_threshold_override BOOLEAN DEFAULT TRUE,  -- Whether threshold can be overwritten
    is_active BOOLEAN DEFAULT TRUE,
    has_fix_button BOOLEAN DEFAULT FALSE,
    has_fix_sql BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);


-- Create table to store applied rule values
CREATE TABLE IF NOT EXISTS data_schema.applied_rules (
    applied_rule_id NUMBER AUTOINCREMENT PRIMARY KEY,
    rule_id VARCHAR(100) NOT NULL,
    threshold_value NUMBER NOT NULL,
    applied_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    applied_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (rule_id) REFERENCES data_schema.config_rules(rule_id)
);


-- Insert predefined configuration rules for warehouses
INSERT INTO data_schema.config_rules (rule_id, rule_name, rule_description, rule_type, check_parameter, comparison_operator, unit, default_threshold, allow_threshold_override, has_fix_button, has_fix_sql)
SELECT 'MAX_STATEMENT_TIMEOUT', 'Max Statement Timeout in Seconds', 'Maximum allowed statement timeout for warehouses', 'Warehouse', 'STATEMENT_TIMEOUT_IN_SECONDS', 'MAX', 'seconds', 300, TRUE, TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM data_schema.config_rules WHERE rule_id = 'MAX_STATEMENT_TIMEOUT')
UNION ALL
SELECT 'MAX_AUTO_SUSPEND', 'Max Auto Suspend in Seconds', 'Maximum allowed auto suspend time for warehouses', 'Warehouse', 'AUTO_SUSPEND', 'MAX', 'seconds', 30, TRUE, TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM data_schema.config_rules WHERE rule_id = 'MAX_AUTO_SUSPEND')
UNION ALL
SELECT 'ZERO_STATEMENT_TIMEOUT', '0 Statement Timeout in Seconds', 'Maximum allowed statement timeout for warehouses', 'Warehouse', 'STATEMENT_TIMEOUT_IN_SECONDS', 'NOT_EQUALS', 'seconds', 0, FALSE, TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM data_schema.config_rules WHERE rule_id = 'ZERO_STATEMENT_TIMEOUT');

-- Insert predefined configuration rules for database objects
INSERT INTO data_schema.config_rules (rule_id, rule_name, rule_description, rule_type, check_parameter, comparison_operator, unit, default_threshold, allow_threshold_override, has_fix_button, has_fix_sql)
SELECT 'MAX_TABLE_RETENTION_TIME', 'Max Table Retention Time in Days', 'Maximum allowed data retention time for tables', 'Database', 'DATA_RETENTION_TIME_IN_DAYS', 'MAX', 'days', 1, TRUE, FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM data_schema.config_rules WHERE rule_id = 'MAX_TABLE_RETENTION_TIME')
UNION ALL
SELECT 'MAX_SCHEMA_RETENTION_TIME', 'Max Schema Retention Time in Days', 'Maximum allowed data retention time for schemas', 'Database', 'DATA_RETENTION_TIME_IN_DAYS', 'MAX', 'days', 1, TRUE, FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM data_schema.config_rules WHERE rule_id = 'MAX_SCHEMA_RETENTION_TIME')
UNION ALL
SELECT 'MAX_DATABASE_RETENTION_TIME', 'Max Database Retention Time in Days', 'Maximum allowed data retention time for databases', 'Database', 'DATA_RETENTION_TIME_IN_DAYS', 'MAX', 'days', 1, TRUE, FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM data_schema.config_rules WHERE rule_id = 'MAX_DATABASE_RETENTION_TIME');


-- Create view for easier data access
CREATE OR REPLACE VIEW data_schema.warehouse_monitor_view AS
SELECT * FROM data_schema.warehouse_details
ORDER BY name,capture_timestamp DESC;

-- CREATE WAREHOUSE TO BE USED BY STREAMLIT ONLY
CREATE WAREHOUSE IF NOT EXISTS CONFIG_RULES_VW
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 30
  AUTO_RESUME = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 600
  INITIALLY_SUSPENDED = TRUE;


-- Create managed task in data_schema (tasks cannot be in versioned schemas)
-- Managed tasks are serverless and use Snowflake-managed compute
CREATE OR REPLACE TASK data_schema.warehouse_monitor_task
    USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'XSMALL'
    SCHEDULE = 'USING CRON 0 7 * * * America/New_York'
AS
BEGIN
  -- Show warehouses to populate result set
  truncate table data_schema.warehouse_details;
  SHOW WAREHOUSES;
  
  -- Insert warehouse details directly from SHOW WAREHOUSES result
  INSERT INTO data_schema.warehouse_details (
    capture_timestamp, name, type, size, min_cluster_count, max_cluster_count,
    auto_suspend, created_on, resumed_on, updated_on, owner, scaling_policy, comment,
    max_concurrency_level, statement_queued_timeout_in_seconds, statement_timeout_in_seconds
  )
  SELECT 
    CURRENT_TIMESTAMP(),
    "name",
    "type",
    "size",
    "min_cluster_count",
    "max_cluster_count",
    "auto_suspend",
    "created_on",
    "resumed_on",
    "updated_on",
    "owner",
    "scaling_policy",
    "comment",
    NULL as max_concurrency_level,
    NULL as statement_queued_timeout_in_seconds,
    NULL as statement_timeout_in_seconds
  FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
END;

-- Resume the task
ALTER TASK data_schema.warehouse_monitor_task RESUME;

--EXECUTE TASK data_schema.warehouse_monitor_task;


-- Create managed task to monitor database, schema, and table retention times
-- Managed tasks are serverless and use Snowflake-managed compute
CREATE OR REPLACE TASK data_schema.db_retention_monitor_task
    USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'XSMALL'
    SCHEDULE = 'USING CRON 0 7 * * * America/New_York'
AS
BEGIN
  -- Truncate the table before inserting new data
  TRUNCATE TABLE data_schema.database_retention_details;
  
  -- Insert database retention details
  INSERT INTO data_schema.database_retention_details (
    object_type, capture_timestamp, database_name, schema_name, table_name,
    data_retention_time_in_days, owner, created_on, last_altered, comment
  )
  SELECT 
    'DATABASE' as object_type,
    CURRENT_TIMESTAMP(),
    database_name,
    NULL as schema_name,
    NULL as table_name,
    retention_time,
    database_owner,
    created,
    last_altered,
    comment
  FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASES
  WHERE deleted IS NULL 
    AND type not in ('APPLICATION','APPLICATION PACKAGE','IMPORTED DATABASE');

  -- Insert schema retention details
  INSERT INTO data_schema.database_retention_details (
    object_type, capture_timestamp, database_name, schema_name, table_name,
    data_retention_time_in_days, owner, created_on, last_altered, comment
  )
  SELECT 
    'SCHEMA' as object_type,
    CURRENT_TIMESTAMP(),
    catalog_name,
    schema_name,
    NULL as table_name,
    retention_time,
    schema_owner,
    created,
    last_altered,
    comment
  FROM SNOWFLAKE.ACCOUNT_USAGE.SCHEMATA
  WHERE deleted IS NULL 
    AND catalog_name in (
      select database_name from data_schema.database_retention_details
      where object_type = 'DATABASE'
    );
  
  -- Insert table retention details
  INSERT INTO data_schema.database_retention_details (
    object_type, capture_timestamp, database_name, schema_name, table_name, table_type,
    data_retention_time_in_days, owner, created_on, last_altered, 
    row_count, bytes, comment
  )
  SELECT 
    'TABLE' as object_type,
    CURRENT_TIMESTAMP(),
    table_catalog,
    table_schema,
    table_name,
    table_type,
    retention_time,
    table_owner,
    created,
    last_altered,
    row_count,
    bytes,
    comment
  FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
  WHERE deleted IS NULL
    AND table_type IN ('BASE TABLE', 'TRANSIENT')
    AND table_catalog in (
      select database_name from data_schema.database_retention_details
      where object_type = 'DATABASE'
    );
END;

-- Resume the task
ALTER TASK data_schema.db_retention_monitor_task RESUME;

EXECUTE TASK data_schema.db_retention_monitor_task;

-- Create internal stage for Streamlit files
CREATE STAGE IF NOT EXISTS core.streamlit_stage
  DIRECTORY = (ENABLE = TRUE);

COPY FILES INTO @core.streamlit_stage/streamlit/ FROM @SNOWFLAKE_CONFIG_RULES_PKG.APP_SRC.STAGE/streamlit/;


-- Create Streamlit app
-- Note: Query warehouse must be provided when launching the Streamlit app

CREATE OR REPLACE STREAMLIT core.config_rules_app
  FROM '@core.streamlit_stage/streamlit/'
  QUERY_WAREHOUSE = 'CONFIG_RULES_VW'
  TITLE = 'Warehouse Monitor App'
  MAIN_FILE = 'app.py';

-- Grant streamlit usage to config_rules_admin role


-- Handling all grants
GRANT ALL ON SCHEMA data_schema TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON SCHEMA core TO APPLICATION ROLE config_rules_admin;
GRANT USAGE ON STREAMLIT core.config_rules_app TO APPLICATION ROLE config_rules_admin;
GRANT READ ON STAGE core.streamlit_stage TO APPLICATION ROLE config_rules_admin;
GRANT WRITE ON STAGE core.streamlit_stage TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON TASK data_schema.warehouse_monitor_task TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON TASK data_schema.db_retention_monitor_task TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON WAREHOUSE CONFIG_RULES_VW TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON TABLE data_schema.warehouse_details TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON TABLE data_schema.database_retention_details TO APPLICATION ROLE config_rules_admin;
GRANT SELECT ON VIEW data_schema.warehouse_monitor_view TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON TABLE data_schema.config_rules TO APPLICATION ROLE config_rules_admin;
GRANT ALL ON TABLE data_schema.applied_rules TO APPLICATION ROLE config_rules_admin;
