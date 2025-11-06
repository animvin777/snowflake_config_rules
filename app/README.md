# Snowflake Config Rules

## Overview

Snowflake Config Rules is a Snowflake Native App that helps you define, apply, and enforce configuration compliance rules across all warehouses in your Snowflake account. The app automatically monitors warehouse configurations, identifies non-compliant warehouses, and generates SQL scripts to remediate issues.

## What This App Does

- **Define Configuration Rules**: Set up rules for warehouse parameters like auto-suspend time and statement timeout
- **Apply Rules with Thresholds**: Apply rules with specific threshold values that warehouses must comply with
- **Automated Monitoring**: Runs a scheduled task to capture warehouse configurations periodically
- **Compliance Dashboard**: Interactive Streamlit app that highlights compliant and non-compliant warehouses
- **SQL Generation**: Automatically generates SQL statements to fix non-compliant warehouses
- **Extensible Architecture**: Easily add new rules by inserting records into the config_rules table

## Key Features

### 1. Rule Configuration Tab
- View all available configuration rules
- Apply rules with custom threshold values
- Manage currently applied rules
- Generate SQL to fix all non-compliant warehouses for a specific rule
- Deactivate rules when no longer needed

### 2. Compliance View Tab
- Real-time compliance status for all warehouses
- Summary metrics (Total, Compliant, Non-Compliant warehouses)
- Filter views: All Warehouses, Non-Compliant Only, or Compliant Only
- Detailed violation information for each warehouse
- Generate fix SQL per warehouse with a single click

### 3. Warehouse Overview Tab
- Complete inventory of all warehouses
- Visual analytics showing warehouse distribution by size and type
- Quick reference for warehouse configurations

## Built-in Configuration Rules

The app comes with two pre-configured rules that can be immediately applied:

### 1. Max Statement Timeout in Seconds
- **Purpose**: Ensures warehouses don't have statement timeouts exceeding your organization's standards
- **Parameter**: `STATEMENT_TIMEOUT_IN_SECONDS`
- **Operator**: MAX (warehouse value must be <= threshold)
- **Example**: Set threshold to 600 seconds to ensure no warehouse can run queries longer than 10 minutes

### 2. Max Auto Suspend in Seconds
- **Purpose**: Prevents warehouses from staying idle too long, reducing unnecessary compute costs
- **Parameter**: `AUTO_SUSPEND`
- **Operator**: MAX (warehouse value must be <= threshold)
- **Example**: Set threshold to 300 seconds to ensure warehouses suspend within 5 minutes of inactivity

## How to Use

### Initial Setup

1. **Install the App** in your Snowflake account
2. **Grant Required Privileges** (automatically requested during installation):
   - CREATE WAREHOUSE
   - EXECUTE TASK
   - MANAGE WAREHOUSES
   - EXECUTE MANAGED TASK
   - MODIFY (to alter warehouse configurations)

### Applying Configuration Rules

1. Navigate to the **Rule Configuration** tab
2. Select a rule from the dropdown (e.g., "Max Auto Suspend in Seconds")
3. Enter your desired threshold value
4. Click **Apply Rule**
5. The rule is now active and monitoring will begin

### Monitoring Compliance

1. Go to the **Compliance View** tab
2. Review the summary metrics at the top
3. Use the filter to focus on non-compliant warehouses
4. For each non-compliant warehouse, you'll see:
   - Current configuration value
   - Required threshold value
   - Specific violations

### Generating Remediation SQL

**Option 1: Per Rule (All Non-Compliant Warehouses)**
1. In the **Rule Configuration** tab
2. Find the applied rule
3. Click **Generate SQL**
4. Copy and execute the generated SQL script

**Option 2: Per Warehouse**
1. In the **Compliance View** tab
2. Find a non-compliant warehouse
3. Click **Generate Fix SQL**
4. Copy and execute the generated SQL for that specific warehouse

### Example Remediation SQL

```sql
-- Generated SQL to fix auto_suspend violations
ALTER WAREHOUSE COMPUTE_WH
SET AUTO_SUSPEND = 300;

ALTER WAREHOUSE DATA_LOAD_WH
SET AUTO_SUSPEND = 300;
```

## Adding New Configuration Rules

The app is designed to be easily extensible. To add a new rule:

1. Insert a new record into the `config_rules` table:

```sql
INSERT INTO data_schema.config_rules (
    rule_id, 
    rule_name, 
    rule_description, 
    warehouse_parameter, 
    comparison_operator, 
    unit
)
VALUES (
    'MIN_AUTO_SUSPEND',  -- Unique identifier
    'Min Auto Suspend in Seconds',  -- Display name
    'Minimum required auto suspend time for warehouses',  -- Description
    'AUTO_SUSPEND',  -- Warehouse parameter to check
    'MIN',  -- Comparison operator (MAX, MIN, or EQUALS)
    'seconds'  -- Unit for display
);
```

2. Update the `check_compliance()` function in the Streamlit app to handle the new parameter (if it's a new warehouse parameter not already monitored)

3. Update the `generate_fix_sql()` function to generate appropriate SQL for the new parameter

## Supported Comparison Operators

- **MAX**: Warehouse value must be less than or equal to threshold
- **MIN**: Warehouse value must be greater than or equal to threshold
- **EQUALS**: Warehouse value must exactly match threshold

## Data Collection Schedule

The app runs a scheduled task to capture warehouse configurations:
- **Frequency**: Every 2 hours (can be modified in setup_script.sql)
- **Initial Run**: Executed immediately during installation
- **Manual Refresh**: Use the "🔄 Refresh Data" button in the Streamlit app

## Post-Installation Setup (Optional)

### Enable Enhanced Parameter Monitoring

By default, the app captures basic warehouse information from `SHOW WAREHOUSES`, including the `AUTO_SUSPEND` parameter. To also capture additional warehouse-specific parameters like **max_concurrency_level**, **statement_timeout_in_seconds**, and **statement_queued_timeout_in_seconds**, you can create an additional task in your account.

#### Why is this optional?

Due to Snowflake Native App security restrictions, the app cannot directly execute `SHOW PARAMETERS FOR WAREHOUSE` on warehouses in your account. If you want to monitor rules based on `statement_timeout_in_seconds`, you need to create a task in your account that runs with your account's privileges.

#### Setup Steps

Run the following SQL in your account after installing the app:

```sql
USE ROLE ACCOUNTADMIN;
USE APPLICATION snowflake_config_rules_app;  -- Choose a database where you want to create the task

-- Create a task that runs after the app's monitoring task
CREATE OR REPLACE TASK data_schema.warehouse_params_monitor_task
    USER_TASK_TIMEOUT_MS = 3600000
    WAREHOUSE = CONFIG_RULES_VW  -- Or use your own warehouse
    SCHEDULE = 'USING CRON 10 7 * * * America/New_York'  -- Run 10 min after the main task
AS
DECLARE
  wh_name VARCHAR;
  wh_cursor CURSOR FOR 
    SELECT DISTINCT name 
    FROM snowflake_config_rules_app.data_schema.warehouse_details 
    WHERE capture_timestamp >= DATEADD(HOUR, -3, CURRENT_TIMESTAMP());
BEGIN
  FOR wh_rec IN wh_cursor DO
    wh_name := wh_rec.name;
    
    BEGIN
      -- Get parameters for this warehouse
      SHOW PARAMETERS IN WAREHOUSE IDENTIFIER(:wh_name);
      
      -- Update the warehouse_details table with parameter values
      MERGE INTO snowflake_config_rules_app.data_schema.warehouse_details tgt
      USING (
        SELECT 
          :wh_name as warehouse_name,
          MAX(CASE WHEN "key" = 'MAX_CONCURRENCY_LEVEL' THEN TRY_CAST("value" AS NUMBER) END) as max_concurrency,
          MAX(CASE WHEN "key" = 'STATEMENT_QUEUED_TIMEOUT_IN_SECONDS' THEN TRY_CAST("value" AS NUMBER) END) as queued_timeout,
          MAX(CASE WHEN "key" = 'STATEMENT_TIMEOUT_IN_SECONDS' THEN TRY_CAST("value" AS NUMBER) END) as stmt_timeout
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
      ) src
      ON tgt.name = src.warehouse_name 
        AND tgt.capture_timestamp >= DATEADD(HOUR, -3, CURRENT_TIMESTAMP())
      WHEN MATCHED THEN UPDATE SET
        tgt.max_concurrency_level = src.max_concurrency,
        tgt.statement_queued_timeout_in_seconds = src.queued_timeout,
        tgt.statement_timeout_in_seconds = src.stmt_timeout;
    EXCEPTION
      WHEN OTHER THEN
        -- Skip warehouses we don't have access to
        CONTINUE;
    END;
  END FOR;
END;

-- Resume the parameter monitoring task
ALTER TASK data_schema.warehouse_params_monitor_task RESUME;

-- Execute tasks to populate initial data
EXECUTE TASK snowflake_config_rules_app.data_schema.warehouse_monitor_task;
EXECUTE TASK snowflake_config_rules_app.data_schema.warehouse_params_monitor_task;
```

This task will:
- Run automatically every 2 hours, 10 minutes after the app's monitoring task
- Query warehouse parameters for all warehouses captured in the most recent collection
- Update the `warehouse_details` table with the parameter values
- Skip any warehouses you don't have access to

To verify parameters are being captured:
```sql
SELECT name, size, auto_suspend, statement_timeout_in_seconds, 
       max_concurrency_level, statement_queued_timeout_in_seconds
FROM snowflake_config_rules_app.data_schema.warehouse_details
WHERE capture_timestamp >= DATEADD(HOUR, -3, CURRENT_TIMESTAMP());
```

## Architecture

### Database Schema

**data_schema.warehouse_details**
- Stores current warehouse configurations captured from `SHOW WAREHOUSES`
- Updated every 2 hours by the monitoring task

**data_schema.config_rules**
- Stores available configuration rules that can be applied
- Pre-populated with two rules (Max Statement Timeout, Max Auto Suspend)
- Can be extended by inserting new rule definitions

**data_schema.applied_rules**
- Stores rules that have been applied with their threshold values
- Tracks when rules were applied and by whom
- Supports rule versioning (deactivating old rules when new thresholds are set)

### Security

- All data is stored with 0-day retention for compliance
- The app requests only necessary privileges
- Consumer controls which rules to apply and when
- SQL generation is read-only; consumer must execute remediation scripts

## Troubleshooting

**Problem**: No warehouse data showing in the app
- **Solution**: Wait for the monitoring task to run (every 2 hours), or manually execute: `EXECUTE TASK data_schema.warehouse_monitor_task;`

**Problem**: Statement timeout rule shows all warehouses as non-compliant with NULL values
- **Solution**: Set up the optional parameter monitoring task (see Post-Installation Setup section)

**Problem**: Cannot apply rules
- **Solution**: Ensure the app has been granted the required privileges, particularly MODIFY

**Problem**: Generated SQL doesn't work
- **Solution**: Ensure you're running the SQL with a role that has MODIFY privilege on the warehouses

## Best Practices

1. **Start with Higher Thresholds**: Begin with lenient thresholds and gradually tighten them
2. **Test on Non-Production First**: Apply rules to dev/test warehouses before production
3. **Monitor Trends**: Use the Warehouse Overview tab to understand current configurations
4. **Regular Reviews**: Periodically review and update rule thresholds based on actual usage
5. **Document Exceptions**: If certain warehouses need different settings, document why

## Version History

- **v1.0.0**: Initial release with Max Statement Timeout and Max Auto Suspend rules

## Support

For issues, feature requests, or questions about extending the app with custom rules, please refer to the Snowflake Native App documentation or contact your Snowflake account team.

