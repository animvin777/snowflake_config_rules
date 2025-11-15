# Snowflake Configuration Compliance Manager

A Snowflake Native App for defining, applying, and enforcing configuration compliance rules across all warehouses and databases in your Snowflake account.

[![Snowflake](https://img.shields.io/badge/Snowflake-Native%20App-blue)](https://www.snowflake.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Overview

The Configuration Compliance Manager helps you maintain consistent configurations across your Snowflake environment by:
- 📋 Defining reusable configuration rules with custom thresholds
- 🔍 Monitoring compliance status in real-time  
- 🔧 Automatically remediating violations with one-click fixes
- 📊 Providing visual dashboards for compliance tracking
- ⏱️ Automating data collection with scheduled tasks

---

## ✨ Key Features

### 🎯 Configure Rules
- View all available configuration rules (grouped by Warehouse and Database types)
- Apply rules with custom threshold values
- Quick-apply recommended default rules
- Deactivate rules when no longer needed
- Generate bulk remediation SQL for all violations

### 🏭 Warehouse Compliance
- Real-time compliance status across all warehouses
- Summary metrics dashboard (Total, Compliant, Non-Compliant, Compliance Rate)
- Filter views: All Warehouses, Non-Compliant Only, or Compliant Only
- **One-Click Fix** - Automatically remediate violations
- Toggle between Tile View and List View
- Detailed violation information with current vs. required values

### 🗄️ Database Retention Compliance
- Monitor table, schema, and database retention settings
- Search and filter by database, schema, or table name
- Bulk remediation for multiple tables at once
- SQL preview before execution
- Expandable sections for detailed information

### ⏱️ Scheduled Tasks & Monitoring
- Control all data collection tasks (suspend, resume, execute)
- View execution history for each task (last 3 runs)
- Monitor task status, duration, and error messages
- Automatic discovery of both app and consumer-created tasks
- Serverless managed tasks for cost efficiency

### 📊 Data Explorer
- Inspect all application data in one place
- Collapsible sections for each data table
- Summary statistics and record counts
- Raw data access for troubleshooting

### 🎨 Modern User Interface
- Light and dark mode compatible design
- Clean, minimalistic layout
- Full-width tabs for better visibility
- Responsive design for all screen sizes
- Color-coded compliance status indicators

---

## 🚀 Installation & Setup

### Prerequisites
- Snowflake account with **ACCOUNTADMIN** role (or equivalent privileges)
- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) installed

### Step 1: Deploy the Application

1. **Clone or download this repository**
   ```bash
   cd /path/to/snowflake_config_rules
   ```

2. **Deploy using Snowflake CLI**
   ```bash
   snow app run
   ```

3. **Grant required privileges** (automatically requested during installation):
   - `MANAGE WAREHOUSES` - Monitor and modify warehouse configurations
   - `CREATE WAREHOUSE` - Create the app's compute warehouse
   - `EXECUTE TASK` - Manage scheduled tasks
   - `EXECUTE MANAGED TASK` - Run serverless tasks
   - `IMPORTED PRIVILEGES ON SNOWFLAKE DB` - Access ACCOUNT_USAGE views for retention data

### Step 2: Post-Installation Setup (**Required**)

To enable **complete parameter monitoring** (including `STATEMENT_TIMEOUT_IN_SECONDS`), you must create an additional task in your account. This task runs with your account's privileges to capture warehouse-specific parameters.

> **⚠️ Why is this necessary?**  
> Due to Snowflake Native App security restrictions, the app cannot directly execute `SHOW PARAMETERS FOR WAREHOUSE` on warehouses in your account. This additional task bridges that gap and is **required** for full functionality.

#### Setup SQL

Run the following SQL **immediately after installing the app**:

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE SNOWFLAKE_CONFIG_RULES_APP;  -- Use your app's database name

-- Create a serverless managed task (no warehouse needed!)
CREATE OR REPLACE TASK data_schema.warehouse_params_monitor_task
    USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'XSMALL'
    SCHEDULE = 'USING CRON 10 7 * * * America/New_York'  -- Run daily at 7:10 AM EST
AS
DECLARE
  wh_name VARCHAR;
  wh_cursor CURSOR FOR 
    SELECT DISTINCT name 
    FROM data_schema.warehouse_details 
    WHERE capture_timestamp >= DATEADD(HOUR, -3, CURRENT_TIMESTAMP());
BEGIN
  FOR wh_rec IN wh_cursor DO
    wh_name := wh_rec.name;
    
    BEGIN
      -- Get parameters for this warehouse
      SHOW PARAMETERS IN WAREHOUSE IDENTIFIER(:wh_name);
      
      -- Update the warehouse_details table with parameter values
      MERGE INTO data_schema.warehouse_details tgt
      USING (
        SELECT 
          :wh_name as warehouse_name,
          MAX(CASE WHEN "key" = 'MAX_CONCURRENCY_LEVEL' 
              THEN TRY_CAST("value" AS NUMBER) END) as max_concurrency,
          MAX(CASE WHEN "key" = 'STATEMENT_QUEUED_TIMEOUT_IN_SECONDS' 
              THEN TRY_CAST("value" AS NUMBER) END) as queued_timeout,
          MAX(CASE WHEN "key" = 'STATEMENT_TIMEOUT_IN_SECONDS' 
              THEN TRY_CAST("value" AS NUMBER) END) as stmt_timeout
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

-- Activate the task
ALTER TASK data_schema.warehouse_params_monitor_task RESUME;

-- Grant permissions to the app
GRANT ALL ON TASK data_schema.warehouse_params_monitor_task 
  TO APPLICATION SNOWFLAKE_CONFIG_RULES_APP;

-- Execute both tasks to populate initial data
EXECUTE TASK data_schema.warehouse_monitor_task;
EXECUTE TASK data_schema.warehouse_params_monitor_task;
```

#### Verify Setup

```sql
-- Check that parameters are being captured
SELECT name, size, auto_suspend, statement_timeout_in_seconds, 
       max_concurrency_level, statement_queued_timeout_in_seconds
FROM data_schema.warehouse_details
WHERE capture_timestamp >= DATEADD(HOUR, -3, CURRENT_TIMESTAMP())
LIMIT 10;
```

You should see values populated for `statement_timeout_in_seconds` and other parameters.

---

## 📚 Available Compliance Rules

The application comes with **5 pre-configured rules** ready to apply:

### Warehouse Rules

| Rule Name | Parameter | Operator | Purpose | Recommended Default |
|-----------|-----------|----------|---------|---------------------|
| **Max Statement Timeout** | `STATEMENT_TIMEOUT_IN_SECONDS` | MAX | Prevent queries from running too long, controlling costs and resources | 300 seconds (5 min) |
| **Max Auto Suspend** | `AUTO_SUSPEND` | MAX | Ensure warehouses suspend quickly when idle, reducing unnecessary compute costs | 30 seconds |

**Warehouse Rule Details:**

```
┌────────────────────────────────────────────────────────────────────┐
│ Max Statement Timeout                                              │
├────────────────────────────────────────────────────────────────────┤
│ Compliance Check: warehouse.statement_timeout ≤ threshold          │
│ Example: If threshold = 300 seconds                                │
│   ✓ Compliant:     warehouse has timeout = 180 seconds             │
│   ✗ Non-Compliant: warehouse has timeout = 600 seconds             │
│ Fix Action: ALTER WAREHOUSE xxx SET STATEMENT_TIMEOUT = 300;       │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ Max Auto Suspend                                                   │
├────────────────────────────────────────────────────────────────────┤
│ Compliance Check: warehouse.auto_suspend ≤ threshold               │
│ Example: If threshold = 30 seconds                                 │
│   ✓ Compliant:     warehouse auto-suspends after 20 seconds        │
│   ✗ Non-Compliant: warehouse auto-suspends after 300 seconds       │
│ Fix Action: ALTER WAREHOUSE xxx SET AUTO_SUSPEND = 30;             │
└────────────────────────────────────────────────────────────────────┘
```

### Database Rules

| Rule Name | Parameter | Operator | Purpose | Recommended Default |
|-----------|-----------|----------|---------|---------------------|
| **Max Table Retention** | `RETENTION_TIME` | MAX | Control table-level Time Travel storage costs | 1 day |
| **Max Schema Retention** | `RETENTION_TIME` | MAX | Control schema-level Time Travel storage costs | 1 day |
| **Max Database Retention** | `RETENTION_TIME` | MAX | Control database-level Time Travel storage costs | 1 day |

**Database Rule Details:**

```
┌────────────────────────────────────────────────────────────────────┐
│ Max Table/Schema/Database Retention Time                           │
├────────────────────────────────────────────────────────────────────┤
│ Compliance Check: retention_time ≤ threshold                       │
│ Example: If threshold = 1 day                                      │
│   ✓ Compliant:     table has retention = 0 days                    │
│   ✗ Non-Compliant: table has retention = 7 days                    │
│ Fix Action: ALTER TABLE xxx SET DATA_RETENTION_TIME_IN_DAYS = 1;   │
│                                                                     │
│ 💡 Why This Matters:                                               │
│   - Time Travel storage costs increase with retention duration     │
│   - 7-day retention = 7x storage cost vs 1-day retention          │
│   - Most use cases only need 1-day Time Travel                    │
└────────────────────────────────────────────────────────────────────┘
```

### Rule Operators Explained

```
┌──────────┬─────────────────────────────────────────────────────────┐
│ Operator │ Compliance Logic                                        │
├──────────┼─────────────────────────────────────────────────────────┤
│ MAX      │ Actual value must be ≤ threshold                        │
│          │ Example: auto_suspend ≤ 30 seconds                      │
│          │ Use when: Setting upper limits (max timeout, max size)  │
├──────────┼─────────────────────────────────────────────────────────┤
│ MIN      │ Actual value must be ≥ threshold                        │
│          │ Example: min_cluster_count ≥ 1                          │
│          │ Use when: Ensuring minimum standards (min size, etc.)   │
├──────────┼─────────────────────────────────────────────────────────┤
│ EQUALS   │ Actual value must exactly match threshold               │
│          │ Example: scaling_policy = 'STANDARD'                    │
│          │ Use when: Enforcing exact configurations                │
└──────────┴─────────────────────────────────────────────────────────┘
```

---

## 📖 User Guide

### Quick Start (3 Minutes)

**Step 1:** Apply Default Rules (30 seconds)
- Navigate to **⚙️ Configure Rules** tab
- Click **"🎯 Apply Default Rules"** button
- All 5 rules are applied instantly with recommended values

**Step 2:** View Compliance Status (1 minute)
- Go to **🏭 Warehouse Compliance** tab
- Review the summary metrics at the top
- See which warehouses are compliant vs. non-compliant

**Step 3:** Fix Violations (1.5 minutes)
- Filter to "Non-Compliant Only"
- Click **Fix** button on any warehouse
- Warehouse is automatically remediated
- Status updates immediately

✅ **Done!** You're now enforcing configuration standards.

---

### Common Workflows

#### Workflow 1: Enforce Auto-Suspend Policy Across All Warehouses

```
┌─────────────────┐
│ 1. Configure    │  Navigate to Configure Rules tab
│    Rules Tab    │  Apply "Max Auto Suspend" = 30 seconds
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Warehouse    │  Go to Warehouse Compliance tab
│    Compliance   │  Filter: "Non-Compliant Only"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Remediate    │  Click "Fix" on each warehouse
│    Violations   │  Or use "Generate SQL" for bulk fix
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ✓ Result        │  All warehouses auto-suspend ≤ 30 seconds
│                 │  Reduced idle compute costs
└─────────────────┘
```

**Detailed Steps:**
1. **⚙️ Configure Rules** → Apply "Max Auto Suspend" with threshold `30`
2. **🏭 Warehouse Compliance** → Filter "Non-Compliant Only"
3. Click **Fix** on each warehouse (or use bulk SQL generation)
4. ✅ Result: All warehouses now comply with 30-second auto-suspend
5. **Impact**: Warehouses suspend faster when idle, reducing unnecessary compute costs

---

#### Workflow 2: Reduce Time Travel Storage Costs

```
┌─────────────────┐
│ 1. Configure    │  Apply "Max Table Retention Time" = 1 day
│    Rules Tab    │  
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Database     │  Go to Database Compliance tab
│    Compliance   │  Search for target database (e.g., "PROD_DB")
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Bulk Fix     │  Click "Fix All Non-Compliant Tables"
│                 │  Review SQL preview
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ✓ Result        │  All tables have 1-day retention
│                 │  Reduced Time Travel storage costs
└─────────────────┘
```

**Detailed Steps:**
1. **⚙️ Configure Rules** → Apply "Max Table Retention Time" with threshold `1`
2. **🗄️ Database Compliance** → Search for your database (e.g., "PROD_DB")
3. Click **Fix All Non-Compliant Tables**
4. ✅ Result: All tables now have 1-day retention
5. **Impact**: Reduced storage costs (7-day retention = 7x cost of 1-day)

---

#### Workflow 3: Troubleshoot Task Execution Issues

```
┌─────────────────┐
│ 1. Task Mgmt    │  Go to Scheduled Tasks & Monitoring tab
│    Tab          │  Locate the failing task
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. View         │  Click "View History" button
│    History      │  Review last 3 execution runs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Diagnose     │  Check execution status (succeeded/failed)
│                 │  Review error messages
│                 │  Note: duration in seconds
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Test Fix     │  Click "Execute Now" to test
│                 │  Verify task succeeds
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ✓ Result        │  Task runs successfully on schedule
│                 │  Data collection automated
└─────────────────┘
```

**Detailed Steps:**
1. **⏱️ Scheduled Tasks & Monitoring** → Find the failing task
2. Click **View History** button
3. Review execution status, scheduled time, duration, and error messages
4. Make necessary fixes (e.g., grant privileges, fix SQL)
5. Click **Execute Now** to test the fix
6. ✅ Result: Task runs successfully and data is collected

---

## 🏗️ Architecture

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Snowflake Native App                              │
│                 (Configuration Compliance Manager)                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────┐         ┌──────────────────────┐            │
│  │  Streamlit UI      │◄────────┤  Compliance Logic    │            │
│  │  (5 Tabs)          │         │  (compliance.py)     │            │
│  │  • Configure Rules │         │  • Check compliance  │            │
│  │  • WH Compliance   │         │  • Generate SQL      │            │
│  │  • DB Compliance   │         │  • Validate rules    │            │
│  │  • Task Mgmt       │         └──────────▲───────────┘            │
│  │  • Data Explorer   │                    │                        │
│  └─────────┬──────────┘                    │                        │
│            │                               │                        │
│            ▼                               │                        │
│  ┌─────────────────────────────────────────┴────────────┐           │
│  │         Database Layer (database.py)                 │           │
│  │  • Query execution       • CRUD operations           │           │
│  │  • Task management       • Error handling            │           │
│  └─────────┬────────────────────────────────────────────┘           │
│            │                                                         │
│            ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐           │
│  │             Data Schema (data_schema)                 │           │
│  ├──────────────────────────────────────────────────────┤           │
│  │  📊 warehouse_details                                 │           │
│  │     • Warehouse configurations (size, auto_suspend)   │           │
│  │     • Captured daily via SHOW WAREHOUSES              │           │
│  │                                                       │           │
│  │  📊 table_retention_details                           │           │
│  │     • Table/schema/database retention settings        │           │
│  │     • Captured daily from ACCOUNT_USAGE               │           │
│  │                                                       │           │
│  │  📋 config_rules                                      │           │
│  │     • Available rule definitions                      │           │
│  │     • Pre-populated with 5 rules                      │           │
│  │                                                       │           │
│  │  ✅ applied_rules                                     │           │
│  │     • Active rules with thresholds                    │           │
│  │     • User-managed                                    │           │
│  └─────────▲────────────────────────────────────────────┘           │
│            │                                                         │
│  ┌─────────┴──────────────────────────────────────┐                 │
│  │  Serverless Managed Tasks (Daily 7 AM EST)     │                 │
│  ├────────────────────────────────────────────────┤                 │
│  │  🔄 warehouse_monitor_task                     │                 │
│  │     • Captures warehouse configs               │                 │
│  │     • No warehouse needed (serverless)         │                 │
│  │                                                │                 │
│  │  🔄 db_retention_monitor_task                  │                 │
│  │     • Captures retention settings              │                 │
│  │     • No warehouse needed (serverless)         │                 │
│  └────────────────────────────────────────────────┘                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
   ┌────────────────────┐              ┌──────────────────────┐
   │ SHOW WAREHOUSES    │              │ ACCOUNT_USAGE        │
   │ (Snowflake Metadata)│              │ (Retention Data)     │
   └────────────────────┘              └──────────────────────┘
              │                                    │
              ▼                                    ▼
   ┌────────────────────────────────────────────────────────┐
   │ Consumer-Created Task (Daily 7:10 AM EST)              │
   │ warehouse_params_monitor_task                          │
   │ • Captures warehouse parameters (statement timeout)    │
   │ • Created during post-installation setup               │
   └────────────────────────────────────────────────────────┘
```

### Directory Structure

```
app/
├── manifest.yml                    # App permissions and configuration
├── setup_script.sql                # Database schema and task definitions
├── README.md                       # User documentation
└── streamlit/
    ├── app.py                     # Main entry point & tab routing
    ├── database.py                # All database operations (CRUD)
    ├── compliance.py              # Compliance checking & SQL generation
    ├── ui_utils.py                # Reusable UI components (header, footer)
    ├── styles.css                 # Light/Dark mode adaptive styling
    ├── tab_rule_config.py         # ⚙️ Configure Rules tab
    ├── tab_wh_compliance.py       # 🏭 Warehouse Compliance tab
    ├── tab_database_compliance.py # 🗄️ Database Compliance tab
    ├── tab_task_management.py     # ⏱️ Scheduled Tasks tab
    └── tab_details.py             # 📊 Data Explorer tab
```



### Database Schema Details

| Table | Purpose | Columns | Update Frequency | Storage |
|-------|---------|---------|------------------|---------|
| `warehouse_details` | Warehouse configurations | name, size, type, auto_suspend, statement_timeout, cluster settings | Daily (7 AM EST) | 0-day retention |
| `table_retention_details` | Retention settings | database_name, schema_name, table_name, retention_time | Daily (7 AM EST) | 0-day retention |
| `config_rules` | Rule definitions | rule_id, rule_name, warehouse_parameter, comparison_operator | Static | Permanent |
| `applied_rules` | Active rules | rule_id, threshold_value, applied_at, is_active | User-triggered | Permanent |

### Task Execution Schedule

| Task | Type | Schedule | Compute | Purpose |
|------|------|----------|---------|---------|
| `warehouse_monitor_task` | Managed | Daily 7:00 AM EST | Serverless (XSMALL) | Capture warehouse configurations via SHOW WAREHOUSES |
| `db_retention_monitor_task` | Managed | Daily 7:00 AM EST | Serverless (XSMALL) | Capture retention settings from ACCOUNT_USAGE |
| `warehouse_params_monitor_task` | Consumer-created | Daily 7:10 AM EST | Serverless (XSMALL) | Capture warehouse parameters (statement timeout, etc.) |

**Cost Optimization Benefits:**  
All tasks use **managed compute** (serverless), which:
- ✅ Eliminates idle warehouse charges
- ✅ Reduces task compute costs by 40-50%
- ✅ Automatically scales based on workload
- ✅ Simplifies infrastructure management

---

## 🔧 Troubleshooting

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **No warehouse data showing** | Monitoring task hasn't run yet | Go to **⏱️ Scheduled Tasks** → Click "Execute Now" on `warehouse_monitor_task` → Wait 30 seconds → Refresh |
| **Statement timeout values are NULL** | Parameter monitoring task not set up | Complete **Post-Installation Setup** (see Step 2 above) - this is required! |
| **Cannot apply rules** | Missing MODIFY privilege | Re-run app installation and grant all requested privileges |
| **Fix button doesn't work** | Insufficient privileges or warehouse doesn't exist | Check error message in UI; ensure `MANAGE WAREHOUSES` privilege granted |
| **"No rules applied" message** | Haven't applied any rules yet | Go to **⚙️ Configure Rules** → Click "Apply Default Rules" |
| **High costs after deployment** | Tasks running too frequently or using dedicated warehouses | Verify tasks use managed compute; check execution frequency in **⏱️ Scheduled Tasks** |
| **Task execution failures** | Privilege issues or network connectivity | Go to **⏱️ Scheduled Tasks** → View History → Check error messages |

### Diagnostic Queries

**Check Task Execution History:**
```sql
SELECT * 
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'data_schema.warehouse_monitor_task'
))
ORDER BY scheduled_time DESC
LIMIT 10;
```

**Verify Granted Privileges:**
```sql
SHOW GRANTS TO APPLICATION snowflake_config_rules_app;
```

**Check Warehouse Data Collection:**
```sql
SELECT COUNT(*) as warehouse_count,
       MAX(capture_timestamp) as last_capture
FROM data_schema.warehouse_details;
```

**Verify Parameter Capture:**
```sql
SELECT 
    COUNT(*) as total_warehouses,
    COUNT(statement_timeout_in_seconds) as with_timeout_captured,
    COUNT(auto_suspend) as with_auto_suspend_captured
FROM data_schema.warehouse_details
WHERE capture_timestamp >= DATEADD(HOUR, -24, CURRENT_TIMESTAMP());
```

### Error Messages Decoded

| Error Message | Meaning | Fix |
|---------------|---------|-----|
| `"Insufficient privileges"` | App lacks required permission | Re-run `snow app run` and grant all requested privileges |
| `"Object does not exist"` | Table or warehouse not found | Refresh data via **⏱️ Scheduled Tasks** → Execute Now |
| `"SQL compilation error"` | Invalid SQL syntax (rare) | Report issue on GitHub with full error message |
| `"Column 'name' not found"` | Outdated app version | Update to version 2.1+ (fixed in latest release) |
| `"Access denied"` | Role doesn't have permission | Switch to ACCOUNTADMIN or grant necessary privileges |

### Getting Further Help

1. **Check Execution History**: Navigate to **⏱️ Scheduled Tasks & Monitoring** → Click "View History" for detailed error logs
2. **Review Data**: Go to **📊 Data Explorer** → Expand sections to verify data is being collected
3. **Test Tasks Manually**: Execute tasks on-demand to see immediate results and error messages
4. **GitHub Issues**: [Open an issue](https://github.com/yourrepo/issues) with:
   - Error message
   - Steps to reproduce
   - Screenshots of the issue
5. **Snowflake Support**: Contact your Snowflake account team for platform-level issues

---

## 📖 Best Practices

### Rule Management Best Practices

| Practice | Why | How |
|----------|-----|-----|
| **Start with defaults** | Recommended values based on common use cases | Click "Apply Default Rules" button |
| **Test in dev first** | Avoid impacting production workloads | Apply rules to dev environment, observe for 1 week |
| **Document exceptions** | Track warehouses that need special config | Use spreadsheet or comments in Snowflake |
| **Review quarterly** | Adjust thresholds as usage patterns change | Export compliance data, analyze trends |
| **Gradual rollout** | Minimize disruption to users | Apply to 10% of warehouses, then expand |

### Cost Optimization Strategies

```
┌───────────────────────────────────────────────────────────────┐
│ Cost Optimization Checklist                                   │
├───────────────────────────────────────────────────────────────┤
│ ✅ Set auto-suspend to 30-60 seconds for most warehouses     │
│    Impact: 40-60% reduction in idle compute costs            │
│                                                               │
│ ✅ Use 1-day retention unless Time Travel is critical        │
│    Impact: 85% reduction in storage costs (vs 7-day default) │
│                                                               │
│ ✅ Monitor task execution frequency (daily is sufficient)    │
│    Impact: Prevent unnecessary task executions               │
│                                                               │
│ ✅ Use serverless managed tasks for all scheduled jobs       │
│    Impact: 40-50% cost reduction vs dedicated warehouses     │
│                                                               │
│ ✅ Review compliance monthly via Data Explorer tab           │
│    Impact: Identify and fix cost leaks early                 │
└───────────────────────────────────────────────────────────────┘
```

### Security Best Practices

| Practice | Implementation |
|----------|----------------|
| **Limit admin access** | Grant `config_rules_admin` role only to authorized users |
| **Audit rules quarterly** | Review applied rules and their business justification |
| **Preview SQL before bulk ops** | Always use "Show SQL" feature before fixing 100+ resources |
| **Use least privilege** | Grant only necessary privileges to the app |
| **Monitor fix actions** | Track who fixed what via Snowflake query history |


## 🔒 Security & Compliance

### Data Privacy
- ✅ All application data stored with **0-day retention** for compliance
- ✅ No sensitive data (queries, results, PII) is captured
- ✅ Only metadata (warehouse names, sizes, configs) is collected

### Privilege Model
- ✅ App requests **only necessary privileges** via manifest
- ✅ Consumer explicitly grants privileges during installation
- ✅ Fix button executes SQL with **consumer's privileges** (not app's)
- ✅ Manual SQL generation is **read-only** (consumer must approve execution)

### Access Control
- ✅ `config_rules_admin` role controls who can apply rules
- ✅ All actions auditable via Snowflake query history
- ✅ No external network access required

---

## 📋 Version History

| Version | Release Date | Key Changes | Impact |
|---------|--------------|-------------|--------|
| **v2.3** | Nov 2025 | Migrated all tasks to managed (serverless) | 40-50% cost reduction |
| **v2.2** | Nov 2025 | Added "Apply Default Rules" button; Data Explorer tab | Faster onboarding |
| **v2.1** | Nov 2025 | Task execution history; dynamic task discovery; bug fixes | Better observability |
| **v2.0** | Nov 2025 | Added database rules (retention); Task Management tab; rule types | Database compliance support |
| **v1.2** | Oct 2025 | Auto-fix button; modular code; refresh buttons; minimalistic UI | Improved UX |
| **v1.0** | Sep 2025 | Initial release with 2 warehouse rules | First public release |

---

### Useful Links
- [Snowflake Native Apps](https://docs.snowflake.com/en/developer-guide/native-apps/native-apps-about)
- [Snowflake CLI Documentation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index)
- [Managed Tasks Guide](https://docs.snowflake.com/en/user-guide/tasks-managed)
- [Time Travel & Retention](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Warehouse Management](https://docs.snowflake.com/en/user-guide/warehouses)

---

**📅 Last Updated:** November 14, 2025  
**🏷️ Current Version:** 2.3  
