# Configuration Compliance Manager

Welcome to the Configuration Compliance Manager! This app helps you enforce consistent configuration standards across all warehouses and databases in your Snowflake account.

---

## 🎯 What This App Does

Monitor and enforce configuration compliance across your Snowflake environment:
- 📋 **Apply Rules** - Set standards for warehouse and database configurations
- 🔍 **Monitor Compliance** - Real-time visibility into compliant and non-compliant resources
- 🔧 **Auto-Remediate** - One-click fixes for violations
- ⏱️ **Automate Collection** - Scheduled tasks keep data up-to-date

---

## ⚡ Quick Start

### Step 1: Complete Post-Installation Setup (**Required**)

To enable complete parameter monitoring (including statement timeouts), you must create an additional task in your account:

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

1. Navigate to **⚙️ Configure Rules** tab
2. Click **"🎯 Apply Default Rules"** button
3. All 5 recommended rules are applied instantly

---

### Step 3: View & Fix Compliance

1. Go to **🏭 Warehouse Compliance** tab
2. Review summary metrics
3. Filter to "Non-Compliant Only"
4. Click **Fix** button on any warehouse to remediate automatically

---

## 📚 Available Rules

### Warehouse Rules

| Rule | What It Controls | Recommended Value | Why It Matters |
|------|------------------|-------------------|----------------|
| **Max Statement Timeout** | How long queries can run before terminating | 300 seconds (5 min) | Prevents runaway queries from consuming resources indefinitely |
| **Max Auto Suspend** | How long warehouses stay idle before suspending | 30 seconds | Reduces costs by suspending inactive warehouses quickly |

**Example: Max Auto Suspend**
```
If threshold = 30 seconds:
  ✓ Compliant:     warehouse auto-suspends after 20 seconds
  ✗ Non-Compliant: warehouse auto-suspends after 300 seconds

Fix Action: ALTER WAREHOUSE xxx SET AUTO_SUSPEND = 30;
Result: Warehouse suspends within 30 seconds of inactivity → Lower costs
```

### Database Rules

| Rule | What It Controls | Recommended Value | Why It Matters |
|------|------------------|-------------------|----------------|
| **Max Table Retention** | Table-level Time Travel duration | 1 day | Reduces storage costs (7-day retention = 7x cost of 1-day) |
| **Max Schema Retention** | Schema-level Time Travel duration | 1 day | Controls retention inheritance for all tables in schema |
| **Max Database Retention** | Database-level Time Travel duration | 1 day | Sets default retention for entire database |

**Example: Max Table Retention**
```
If threshold = 1 day:
  ✓ Compliant:     table has 0-day or 1-day retention
  ✗ Non-Compliant: table has 7-day retention

Fix Action: ALTER TABLE xxx SET DATA_RETENTION_TIME_IN_DAYS = 1;
Result: Reduced Time Travel storage by ~85%
```

---

## 🎨 Using the App

### ⚙️ Configure Rules Tab

**Purpose:** Define which configuration standards to enforce

**Actions:**
- **View Rules**: See all available rules grouped by type (Warehouse/Database)
- **Apply Rule**: Select a rule, enter threshold value, click "Apply Rule"
- **Apply Defaults**: Click "Apply Default Rules" for instant setup
- **Generate SQL**: Create bulk remediation SQL for all violations
- **Deactivate Rule**: Stop enforcing a rule

**Best Practice:** Start with default rules, then customize based on your needs.

---

### 🏭 Warehouse Compliance Tab

**Purpose:** Monitor and fix warehouse configuration violations

**Features:**
- **Summary Metrics**: Total warehouses, compliant count, compliance rate
- **Filters**: View all, non-compliant only, or compliant only
- **View Modes**: Toggle between Tile View (visual cards) and List View (tabular)
- **One-Click Fix**: Remediate violations automatically
- **Detailed Info**: See current value vs. required threshold for each violation

**Workflow:**
1. Review summary metrics
2. Filter to "Non-Compliant Only"
3. Click **Fix** on each warehouse
4. Status updates immediately to "Compliant"

---

### 🗄️ Database Compliance Tab

**Purpose:** Monitor and fix table/schema/database retention violations

**Features:**
- **Search**: Find specific databases, schemas, or tables
- **Bulk Actions**: Fix all non-compliant tables at once
- **SQL Preview**: Review SQL before executing
- **Expandable Details**: See full configuration for each table

**Workflow:**
1. Search for your database (e.g., "PROD_DB")
2. Review non-compliant tables
3. Click "Fix All Non-Compliant Tables"
4. Confirm SQL preview
5. All tables updated to compliant state

---

### ⏱️ Scheduled Tasks & Monitoring Tab

**Purpose:** Control automated data collection

**Features:**
- **Task List**: View all app and consumer-created tasks
- **Execution History**: Last 3 runs with status, duration, errors
- **Controls**: Suspend, Resume, or Execute Now
- **Status Indicators**: Green = running, Red = suspended

**Tasks Explained:**
- `warehouse_monitor_task`: Captures warehouse configs daily (7 AM EST)
- `db_retention_monitor_task`: Captures retention settings daily (7 AM EST)
- `warehouse_params_monitor_task`: Captures warehouse parameters (created by you in post-install)

**Troubleshooting:**
- If data is missing → Click "Execute Now" on the relevant task
- If task fails → Click "View History" to see error messages

---

### 📊 Data Explorer Tab

**Purpose:** Inspect all application data

**Features:**
- **Warehouse Details**: All captured warehouse configurations
- **Table Retention**: All retention settings
- **Config Rules**: Available rule definitions
- **Applied Rules**: Currently active rules with thresholds
- **Summary Stats**: Record counts and last update times

**Use Cases:**
- Verify data is being collected
- Troubleshoot missing or NULL values
- Export data for external analysis
- Audit rule configurations

---

## 💡 Common Workflows

### Reduce Idle Warehouse Costs

```
Goal: Ensure all warehouses suspend within 30 seconds of inactivity

Steps:
1. ⚙️ Configure Rules → Apply "Max Auto Suspend" = 30
2. 🏭 Warehouse Compliance → Filter "Non-Compliant Only"
3. Click "Fix" on each warehouse
4. ✓ Result: Reduced idle compute costs by 40-60%
```

---

### Control Time Travel Storage Costs

```
Goal: Reduce retention time to 1 day for all production tables

Steps:
1. ⚙️ Configure Rules → Apply "Max Table Retention" = 1
2. 🗄️ Database Compliance → Search "PROD_DB"
3. Click "Fix All Non-Compliant Tables"
4. ✓ Result: Reduced storage costs by ~85%
```

---

### Monitor Rule Compliance Over Time

```
Goal: Track compliance improvements weekly

Steps:
1. 🏭 Warehouse Compliance → Note compliance rate (e.g., 65%)
2. Fix violations over the week
3. Return next week → Compliance rate improved (e.g., 95%)
4. ✓ Result: Demonstrable improvement in governance
```

---

## 🔧 Troubleshooting

### Issue: No warehouse data showing

**Cause:** Monitoring task hasn't run yet  
**Fix:**
1. Go to **⏱️ Scheduled Tasks & Monitoring** tab
2. Click "Execute Now" on `warehouse_monitor_task`
3. Wait 30 seconds
4. Refresh the app

---

### Issue: Statement timeout values are NULL

**Cause:** Post-installation task not created  
**Fix:** Complete **Post-Installation Setup** (see Step 1 above) - this is **required**!

---

### Issue: Fix button doesn't work

**Cause:** Insufficient privileges  
**Fix:**
1. Ensure you granted `MANAGE WAREHOUSES` privilege during installation
2. Check error message displayed in the UI for specific details
3. If needed, re-grant privileges to the app

---

### Issue: "No rules applied" message in compliance tabs

**Cause:** Haven't applied any rules yet  
**Fix:**
1. Go to **⚙️ Configure Rules** tab
2. Click "🎯 Apply Default Rules" button
3. Return to compliance tabs to see results

---

### Issue: High costs after deployment

**Cause:** Tasks misconfigured or rules not applied  
**Fix:**
1. Verify tasks use serverless compute (check **⏱️ Scheduled Tasks** tab)
2. Apply cost-saving rules (Max Auto Suspend = 30 seconds)
3. Review execution frequency (daily is recommended)

---

## 📖 Best Practices

### Rule Management
- ✅ **Start with defaults** - Click "Apply Default Rules" for instant setup
- ✅ **Test in dev first** - Apply to development environment before production
- ✅ **Review monthly** - Check compliance trends and adjust thresholds
- ✅ **Document exceptions** - Track warehouses needing special configurations

### Cost Optimization
- ✅ **Auto-suspend = 30-60 seconds** for most warehouses (reduces idle costs by 40-60%)
- ✅ **Retention = 1 day** unless Time Travel is critical (reduces storage by ~85%)
- ✅ **Monitor task history** - Ensure tasks run successfully without errors
- ✅ **Use serverless tasks** - All tasks should use managed compute

### Security
- ✅ **Review SQL before bulk operations** - Use "Show SQL" feature
- ✅ **Audit quarterly** - Review applied rules and their justification
- ✅ **Limit access** - Grant admin role only to authorized users

---

## 📊 Understanding Metrics

### Compliance Rate

```
Compliance Rate = (Compliant Resources / Total Resources) × 100

Example:
- Total Warehouses: 20
- Compliant: 15
- Non-Compliant: 5
- Compliance Rate: 75%

Goal: Achieve 95%+ compliance rate
```

### Cost Impact Estimation

```
Auto-Suspend Savings:
- Before: Warehouse idles for 300 seconds (5 min) before suspending
- After: Warehouse idles for 30 seconds before suspending
- Savings: 90% reduction in idle time
- Impact: 40-60% lower warehouse costs (depending on usage pattern)

Retention Savings:
- Before: Table has 7-day retention
- After: Table has 1-day retention  
- Savings: 85% reduction in Time Travel storage
- Impact: Significant reduction in monthly storage bills
```

---

## 🎯 Success Metrics

Track these metrics to measure app effectiveness:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Compliance Rate** | >95% | Warehouse Compliance tab → Summary metrics |
| **Cost Reduction** | 30-50% on idle compute | Snowflake cost monitoring (before/after applying rules) |
| **Storage Savings** | 70-85% on Time Travel | Snowflake storage monitoring (before/after retention rules) |
| **Time to Remediate** | <5 minutes | Time from identifying violation to clicking Fix |
| **Task Success Rate** | 100% | Scheduled Tasks tab → Execution history (all succeeded) |

---

## 🔒 Security & Privacy

- ✅ All data stored with **0-day retention** for compliance
- ✅ No PII or sensitive query data captured
- ✅ Only metadata (warehouse names, sizes, configs) collected
- ✅ Fix actions execute with **your privileges** (not app's)
- ✅ All actions auditable via Snowflake query history

---

## 📞 Need Help?

### Within the App
1. **Task Issues**: Go to **⏱️ Scheduled Tasks** → View History → Check error messages
2. **Missing Data**: Go to **📊 Data Explorer** → Verify data collection
3. **SQL Preview**: Use "Show SQL" feature before fixing to review changes

### External Resources
- 📚 [Snowflake Time Travel Docs](https://docs.snowflake.com/en/user-guide/data-time-travel)
- 📚 [Warehouse Management Guide](https://docs.snowflake.com/en/user-guide/warehouses)
- 📚 [Managed Tasks Documentation](https://docs.snowflake.com/en/user-guide/tasks-managed)

---

## 🎓 Learning Resources

### Understanding Rule Operators

```
MAX Operator (Most Common):
  - Rule: Max Auto Suspend = 30 seconds
  - Means: Warehouse value must be ≤ 30 seconds
  - Compliant: auto_suspend = 20 seconds ✓
  - Non-Compliant: auto_suspend = 60 seconds ✗

MIN Operator:
  - Rule: Min Cluster Count = 1
  - Means: Warehouse value must be ≥ 1
  - Compliant: min_cluster_count = 2 ✓
  - Non-Compliant: min_cluster_count = 0 ✗

EQUALS Operator:
  - Rule: Scaling Policy = 'STANDARD'
  - Means: Warehouse value must exactly match
  - Compliant: scaling_policy = 'STANDARD' ✓
  - Non-Compliant: scaling_policy = 'ECONOMY' ✗
```

### Architecture Overview

```
┌──────────────────────────────────────────────┐
│         Your Snowflake Account               │
├──────────────────────────────────────────────┤
│                                              │
│  ┌────────────────────────────────┐          │
│  │  Configuration Compliance App  │          │
│  │  • Monitors warehouses         │          │
│  │  • Checks compliance           │          │
│  │  • Generates fix SQL           │          │
│  └────────────┬───────────────────┘          │
│               │                              │
│               ▼                              │
│  ┌────────────────────────────────┐          │
│  │  Your Warehouses & Databases   │          │
│  │  • Configurations monitored    │          │
│  │  • Violations detected         │          │
│  │  • Fixes applied on demand     │          │
│  └────────────────────────────────┘          │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 📋 Appendix: Rule Reference

### Complete Rule Catalog

| Rule ID | Rule Name | Type | Parameter | Operator | Default |
|---------|-----------|------|-----------|----------|---------|
| `MAX_STATEMENT_TIMEOUT` | Max Statement Timeout in Seconds | Warehouse | STATEMENT_TIMEOUT_IN_SECONDS | MAX | 300 |
| `MAX_AUTO_SUSPEND` | Max Auto Suspend in Seconds | Warehouse | AUTO_SUSPEND | MAX | 30 |
| `MAX_TABLE_RETENTION_TIME` | Max Table Retention Time in Days | Database | RETENTION_TIME | MAX | 1 |
| `MAX_SCHEMA_RETENTION_TIME` | Max Schema Retention Time in Days | Database | RETENTION_TIME | MAX | 1 |
| `MAX_DATABASE_RETENTION_TIME` | Max Database Retention Time in Days | Database | RETENTION_TIME | MAX | 1 |

### Supported Parameters

Parameters already available (no additional setup needed):
- `AUTO_SUSPEND`
- `SIZE`
- `TYPE`
- `MIN_CLUSTER_COUNT`
- `MAX_CLUSTER_COUNT`
- `SCALING_POLICY`

Parameters requiring post-installation setup:
- `STATEMENT_TIMEOUT_IN_SECONDS` (requires consumer-created task)
- `MAX_CONCURRENCY_LEVEL` (requires consumer-created task)
- `STATEMENT_QUEUED_TIMEOUT_IN_SECONDS` (requires consumer-created task)

---

**📅 Last Updated:** November 14, 2025  
**🏷️ Version:** 2.3  
**💡 Tip:** Bookmark this README for quick reference while using the app!
