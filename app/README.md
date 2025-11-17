# Configuration Compliance Manager

Welcome to the Configuration Compliance Manager! This Native App helps you enforce consistent configuration standards across all warehouses, databases, and tables in your Snowflake account.

---

## 📋 What This App Does

```
┌────────────────────────────────────────────────────────────┐
│              Compliance Management Workflow                 │
└────────────────────────────────────────────────────────────┘

    1. DEFINE           2. MONITOR          3. REMEDIATE
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │Configure│────────>│ Check   │────────>│  Fix    │
   │  Rules  │         │Complian │         │Violatio │
   └─────────┘         └─────────┘         └─────────┘
        │                   │                    │
        v                   v                    v
   Set custom         Real-time            One-click
   thresholds         dashboards           or bulk SQL
```

The app provides:

- **Warehouse Compliance**: Monitor and enforce auto-suspend, timeouts, and concurrency limits
- **Database Retention Compliance**: Control Time Travel storage costs by enforcing retention policies
- **Tag Compliance**: Ensure mandatory tags are applied to all objects
- **Whitelist Management**: Handle approved exceptions to your compliance rules
- **Automated Data Collection**: Daily scheduled tasks collect configuration data
- **One-Click Remediation**: Fix violations instantly or generate SQL for bulk operations

---

## ⚡ Quick Start Guide (5 Minutes)

### Step 1: Complete Post-Installation Setup (**Required**)

Due to Snowflake Native App security restrictions, you need to create an additional task in your account to enable complete parameter monitoring.

**Why?** The app cannot directly execute `SHOW PARAMETERS FOR WAREHOUSE` on your warehouses. This task runs with your account privileges to capture those parameters (like `STATEMENT_TIMEOUT_IN_SECONDS`).

**Run this SQL now:**

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE SNOWFLAKE_CONFIG_RULES_APP;  -- Use your app's database name

-- Create serverless task to capture warehouse parameters
CREATE OR REPLACE TASK data_schema.warehouse_params_monitor_task
    USER_TASK_MANAGED_INITIAL_WAREHOUSE_SIZE = 'XSMALL'
    SCHEDULE = 'USING CRON 10 7 * * * America/New_York'
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
      SHOW PARAMETERS IN WAREHOUSE IDENTIFIER(:wh_name);
      MERGE INTO data_schema.warehouse_details tgt
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
      WHEN OTHER THEN CONTINUE;
    END;
  END FOR;
END;

-- Activate and grant permissions
ALTER TASK data_schema.warehouse_params_monitor_task RESUME;
GRANT ALL ON TASK data_schema.warehouse_params_monitor_task TO APPLICATION SNOWFLAKE_CONFIG_RULES_APP;

-- Execute tasks to populate initial data
EXECUTE TASK data_schema.warehouse_monitor_task;
EXECUTE TASK data_schema.warehouse_params_monitor_task;
```

**Verify Setup:**
```sql
SELECT name, auto_suspend, statement_timeout_in_seconds
FROM data_schema.warehouse_details
LIMIT 5;
```

Values for `statement_timeout_in_seconds` should be populated (not NULL).

---

### Step 2: Apply Configuration Rules

1. Navigate to **Configure Rules** tab
2. Click **Apply Default Rules** button
3. All 5 recommended rules are applied instantly with optimal thresholds

---

### Step 3: View & Fix Compliance

1. Go to **Warehouse Compliance** or **Database Compliance** tab
2. Review summary metrics at the top
3. Filter to "Non-Compliant Only" to see violations
4. Click **Fix** button on any object to remediate automatically

✅ **Done!** You're now enforcing configuration standards.

---

## 🔑 Required Privileges & Why

During installation, you granted these privileges to the app:

| Privilege | Why It's Needed | When It's Used |
|-----------|----------------|----------------|
| **CREATE WAREHOUSE** | Creates `CONFIG_RULES_VW` warehouse for app compute | One-time during installation |
| **MANAGE WAREHOUSES** | Allows app to monitor warehouse configs & apply fixes | When viewing compliance & clicking Fix |
| **EXECUTE TASK** | Creates scheduled data collection tasks | One-time during installation |
| **EXECUTE MANAGED TASK** | Runs serverless tasks for automated data collection | Daily at 7 AM EST |
| **IMPORTED PRIVILEGES ON SNOWFLAKE DB** | Accesses `ACCOUNT_USAGE` views for retention data | Daily for database compliance monitoring |

### Security Notes

- ✅ **Zero-day retention**: All app tables use 0-day retention (no data history stored)
- ✅ **Metadata only**: App only collects configuration metadata, never query results or user data
- ✅ **Explicit fixes**: Fix actions only execute when you click the Fix button
- ✅ **Audit trail**: All actions logged in Snowflake query history

---

## 📊 How The App Works

### Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                  Your Snowflake Account                    │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────┐            │
│  │    Configuration Compliance Manager      │            │
│  ├──────────────────────────────────────────┤            │
│  │                                          │            │
│  │  ┌────────────┐     ┌──────────────┐    │            │
│  │  │ Streamlit  │────>│  Compliance  │    │            │
│  │  │    UI      │     │    Engine    │    │            │
│  │  └────────────┘     └──────────────┘    │            │
│  │         │                   │            │            │
│  │         └───────┬───────────┘            │            │
│  │                 │                        │            │
│  │         ┌───────v────────┐               │            │
│  │         │  Data Storage  │               │            │
│  │         ├────────────────┤               │            │
│  │         │ • Warehouses   │               │            │
│  │         │ • Retention    │               │            │
│  │         │ • Tags         │               │            │
│  │         │ • Rules        │               │            │
│  │         │ • Whitelists   │               │            │
│  │         └────────────────┘               │            │
│  └──────────────────────────────────────────┘            │
│                 ▲                                         │
│                 │                                         │
│  ┌──────────────┴──────────────┐                         │
│  │   Automated Data Collection │                         │
│  ├─────────────────────────────┤                         │
│  │ Daily at 7:00 AM EST:       │                         │
│  │ • Warehouse configs          │                         │
│  │ • Database retention         │                         │
│  │ • Tag assignments            │                         │
│  │                             │                         │
│  │ Daily at 7:10 AM EST:       │                         │
│  │ • Warehouse parameters       │                         │
│  │   (via your task)           │                         │
│  └─────────────────────────────┘                         │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Data Collection Flow

```
1. SCHEDULED TASKS RUN
   ↓
2. COLLECT METADATA
   - SHOW WAREHOUSES
   - ACCOUNT_USAGE.TABLES
   - SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
   ↓
3. STORE IN APP TABLES
   - warehouse_details
   - database_retention_details  
   - tag_compliance_details
   ↓
4. COMPLIANCE ENGINE CHECKS
   - Compare actual vs required values
   - Identify violations
   - Exclude whitelisted items
   ↓
5. DISPLAY IN UI
   - Show compliance metrics
   - List violations
   - Enable one-click fixes
```

---

## 🎯 Using The App

### Tab 1: Configure Rules

**Purpose**: Define what compliance standards to enforce

**Actions**:
- View all available rules (Warehouse, Database, Tag types)
- Apply rules with custom thresholds
- Apply default rules with one click
- Deactivate rules you no longer need
- See all currently applied rules with violation counts

**Quick Win**: Click **Apply Default Rules** to instantly set up 5 common rules

---

### Tab 2: Tag Compliance

**Purpose**: Ensure mandatory tags are applied

**Features**:
```
┌─────────────────────────────────────────┐
│  Tag Compliance Dashboard               │
├─────────────────────────────────────────┤
│  📊 Metrics                             │
│  Total │ Compliant │ Non-Compliant │ %  │
│   100  │     85    │      15       │85% │
├─────────────────────────────────────────┤
│  Filter: [All / Non-Compliant / Whitel.]│
│  Object Type: [WAREHOUSE ▼]             │
│  Search: [________________]             │
├─────────────────────────────────────────┤
│  🏭 WH_ANALYTICS                        │
│  ✗ Missing: cost_center                 │
│     [Whitelist] [Generate SQL]          │
└─────────────────────────────────────────┘
```

**Use Case**: Verify all warehouses have a "cost_center" tag for charge-back

---

### Tab 3: Warehouse Compliance

**Purpose**: Monitor and fix warehouse configuration violations

**Features**:
- Summary metrics (Total, Compliant, Non-Compliant, Compliance Rate)
- Filter: All / Non-Compliant / Compliant / Whitelisted
- View: Tile or List
- One-click Fix button per warehouse
- Whitelist exceptions

**Example Violations**:
```
┌──────────────────────────────────────┐
│  WH_PROD                             │
│  Size: LARGE │ Type: STANDARD        │
├──────────────────────────────────────┤
│  ✗ Auto Suspend: 300s (Max: 30s)     │
│  ✗ Statement Timeout: 0s (No limit)  │
├──────────────────────────────────────┤
│  [Fix] [Whitelist] [Show SQL]        │
└──────────────────────────────────────┘
```

Click **Fix** → Auto-suspend and timeout instantly updated

---

### Tab 4: Database Compliance

**Purpose**: Control Time Travel retention across all tables

**Features**:
- Search by database, schema, or table name
- Group violations by database
- Bulk fix all non-compliant tables at once
- Preview SQL before execution

**Use Case**: Set all production tables to 1-day retention to save 85% on storage

```
Database: PROD_DB (523 tables, 487 non-compliant)
 
  SCHEMA_1 (245 tables)
    TABLE_A: 7 days ✗
    TABLE_B: 7 days ✗
    [Fix All]

  SCHEMA_2 (278 tables)  
    TABLE_C: 1 day ✓
    TABLE_D: 7 days ✗
    [Fix All]
```

---

### Tab 5: Scheduled Tasks & Monitoring

**Purpose**: Monitor automated data collection

**Features**:
- Control tasks: Suspend, Resume, Execute Now
- View execution history (last 3 runs)
- See task status, duration, errors
- Manage both app and consumer-created tasks

**Tasks**:
- `warehouse_monitor_task` - Collects warehouse configs
- `db_retention_monitor_task` - Collects retention settings
- `tag_monitor_task` - Collects tag assignments
- `warehouse_params_monitor_task` - Your task for parameters

**Troubleshooting**: If data is missing, click "Execute Now" to run tasks immediately

---

### Tab 6: Whitelist Management

**Purpose**: Manage approved exceptions to compliance rules

**Features**:
- View all whitelisted violations
- Multi-select and remove whitelists
- See why each exception was approved
- Filter by rule type

**Use Case**: ADMIN_WH needs 300-second auto-suspend (exception to 30-second rule)

---

### Tab 7: Data Explorer

**Purpose**: Inspect all collected configuration data

**Features**:
- View all app tables
- See record counts and last update times
- Export data for external analysis
- Verify data collection is working

**Tables**:
- Warehouse Details
- Database Retention Details
- Tag Compliance Details
- Config Rules
- Applied Rules
- Whitelists

---

## 💡 Common Use Cases

### Use Case 1: Reduce Idle Warehouse Costs

```
Goal: Ensure all warehouses suspend within 30 seconds

Steps:
  1. Configure Rules → Apply "Max Auto Suspend" = 30
  2. Warehouse Compliance → Filter "Non-Compliant Only"
  3. Click "Fix" on each warehouse

Result: 40-60% reduction in idle compute costs
Savings: $5,000-$15,000/month (typical for 50 warehouses)
```

---

### Use Case 2: Control Storage Costs

```
Goal: Reduce Time Travel retention to 1 day on all tables

Steps:
  1. Configure Rules → Apply "Max Table Retention" = 1
  2. Database Compliance → Search for database
  3. Click "Fix All Non-Compliant Tables"

Result: 85% reduction in Time Travel storage costs
Savings: $10,000-$30,000/month (typical for large account)
```

---

### Use Case 3: Enforce Tagging for Cost Allocation

```
Goal: Ensure all warehouses have "cost_center" tag

Steps:
  1. Configure Rules → Add Tag Rule (cost_center, WAREHOUSE)
  2. Tag Compliance → View violations
  3. Generate SQL → Apply tags manually

Result: 100% tag coverage for accurate cost allocation
```

---

### Use Case 4: Audit Compliance Monthly

```
Goal: Report compliance rate to management

Steps:
  1. Check each compliance tab
  2. Note metrics: Total, Compliant, Non-Compliant, %
  3. Export Data Explorer tables for detailed analysis

Result: Monthly compliance scorecard
```

---

## 🔧 Troubleshooting

### Issue: No Warehouse Data Showing

**Cause**: Monitoring task hasn't run yet  
**Fix**:
1. Go to **Scheduled Tasks & Monitoring**
2. Find `warehouse_monitor_task`
3. Click "Execute Now"
4. Wait 30 seconds, then refresh

---

### Issue: Statement Timeout Values Are NULL

**Cause**: Post-installation task not created  
**Fix**: Run the SQL from **Step 1** above - this is required!

---

### Issue: Fix Button Doesn't Work

**Cause**: Missing `MANAGE WAREHOUSES` privilege  
**Fix**:
1. Ensure privilege was granted during installation
2. Check error message in UI for specific details
3. If needed, re-grant: `GRANT MANAGE WAREHOUSES TO APPLICATION SNOWFLAKE_CONFIG_RULES_APP`

---

### Issue: "No Rules Applied" Message

**Cause**: Haven't applied any rules yet  
**Fix**:
1. Go to **Configure Rules** tab
2. Click "Apply Default Rules"
3. Return to compliance tabs

---

### Issue: High Costs After Deployment

**Cause**: Misconfigured tasks or rules not applied  
**Fix**:
1. Verify tasks use serverless compute (check **Scheduled Tasks**)
2. Apply cost-saving rules (Max Auto Suspend = 30 seconds)
3. Review execution frequency (daily is recommended)

---

### Issue: Task Execution Failures

**Cause**: Privilege issues or network connectivity  
**Fix**:
1. Go to **Scheduled Tasks & Monitoring**
2. Click "View History" on failing task
3. Review error message
4. Common fixes:
   - Grant missing privileges
   - Check warehouse exists
   - Verify network access

---

## 📊 Understanding Metrics

### Compliance Rate Calculation

```
Compliance Rate = (Compliant Objects / Total Objects) × 100

Example:
  Total Warehouses: 50
  Compliant: 38
  Non-Compliant: 10
  Whitelisted: 2
  
  Compliance Rate: (38 + 2) / 50 × 100 = 80%
  (Whitelisted count as compliant)
```

### Cost Impact Estimation

#### Auto-Suspend Savings
```
Before: Warehouse idles for 300 seconds before suspending
After:  Warehouse idles for 30 seconds before suspending

Savings: 90% reduction in idle time
Impact:  40-60% lower warehouse costs
         (depending on usage pattern)

Example: 20 warehouses × $2/hour × 10 idle hours/day × 30% idle time reduction
         = $3,600/month savings
```

#### Retention Savings
```
Before: Tables have 7-day retention  
After:  Tables have 1-day retention

Savings: 85% reduction in Time Travel storage
Impact:  Significant monthly storage bill reduction

Example: 1 TB data × 7 days × $23/TB/month = $161/month
         1 TB data × 1 day × $23/TB/month = $23/month
         Savings: $138/month per TB
```

---

## 📈 Best Practices

### 1. Start with Default Rules

- Click **Apply Default Rules** for instant setup
- Recommended thresholds based on common use cases
- Adjust later based on your specific needs

### 2. Test in Dev First

- Apply rules to dev/test environment first
- Observe for 1 week
- Adjust thresholds if needed
- Then roll out to production

### 3. Use Whitelists for Valid Exceptions

- Don't just disable rules entirely
- Whitelist specific objects that need exceptions
- Document reason for each whitelist
- Review quarterly

### 4. Monitor Regularly

- Check compliance dashboards weekly
- Review task execution history monthly
- Export data for trend analysis
- Adjust thresholds as usage patterns change

### 5. Communicate Changes

- Notify teams before applying new rules
- Explain business benefits (cost savings, governance)
- Provide grace period before enforcement
- Track and report improvements

---

## 🎓 Understanding Rule Operators

### MAX Operator (Most Common)

```
Rule: Max Auto Suspend = 30 seconds
Logic: Actual value must be ≤ 30 seconds

✓ Compliant:     auto_suspend = 20 seconds (less than limit)
✗ Non-Compliant: auto_suspend = 60 seconds (exceeds limit)

Fix: ALTER WAREHOUSE xxx SET AUTO_SUSPEND = 30;
```

### MIN Operator

```
Rule: Min Cluster Count = 1  
Logic: Actual value must be ≥ 1

✓ Compliant:     min_cluster_count = 2 (meets minimum)
✗ Non-Compliant: min_cluster_count = 0 (below minimum)

Fix: ALTER WAREHOUSE xxx SET MIN_CLUSTER_COUNT = 1;
```

### NOT_EQUALS Operator

```
Rule: Statement Timeout ≠ 0 (No unlimited timeouts)
Logic: Actual value must not equal 0

✓ Compliant:     statement_timeout = 300 (has limit)
✗ Non-Compliant: statement_timeout = 0 (unlimited)

Fix: ALTER WAREHOUSE xxx SET STATEMENT_TIMEOUT_IN_SECONDS = 300;
```

---

## 📋 Available Rules Reference

### Warehouse Rules

| Rule | Parameter | Operator | Default | Purpose |
|------|-----------|----------|---------|---------|
| Max Statement Timeout | STATEMENT_TIMEOUT_IN_SECONDS | MAX | 300 | Prevent runaway queries |
| Max Auto Suspend | AUTO_SUSPEND | MAX | 30 | Reduce idle costs |
| Zero Statement Timeout | STATEMENT_TIMEOUT_IN_SECONDS | NOT_EQUALS | 0 | Require query timeouts |

### Database Rules

| Rule | Level | Operator | Default | Purpose |
|------|-------|----------|---------|---------|
| Max Table Retention | Table | MAX | 1 | Control storage costs |
| Max Schema Retention | Schema | MAX | 1 | Control storage costs |
| Max Database Retention | Database | MAX | 1 | Control storage costs |

### Tag Rules

| Rule | Objects | Purpose |
|------|---------|---------|
| Missing Tag Value | WAREHOUSE, DATABASE, TABLE | Ensure mandatory tags applied |

---

## 🔗 Additional Resources

- [Snowflake Time Travel Documentation](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Warehouse Management Guide](https://docs.snowflake.com/en/user-guide/warehouses)
- [Managed Tasks Documentation](https://docs.snowflake.com/en/user-guide/tasks-managed)
- [Tag-Based Masking](https://docs.snowflake.com/en/user-guide/tag-based-masking)

---

## 📞 Support

**Within the App**:
- Check **Scheduled Tasks & Monitoring** → View History for error details
- Review **Data Explorer** to verify data collection
- Use "Show SQL" feature to preview changes

**External**:
- GitHub Issues: [Report a bug](https://github.com/animvin777/snowflake_config_rules/issues)
- Documentation: See main [README](https://github.com/animvin777/snowflake_config_rules)

---

**Last Updated**: November 17, 2025  
**App Version**: 2.3  
**Recommended For**: All Snowflake accounts with 10+ warehouses or 100+ tables

💡 **Pro Tip**: Start by applying default rules and monitoring for 1 week before making adjustments. Most organizations see immediate cost savings with zero operational impact.
