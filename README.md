# Snowflake Configuration Compliance Manager

A comprehensive Snowflake Native Application for automated configuration compliance management across your entire Snowflake environment. Define, monitor, and enforce configuration standards for warehouses, databases, and tables while ensuring proper tagging compliance.

[![Snowflake](https://img.shields.io/badge/Snowflake-Native%20App-blue)](https://www.snowflake.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.3-blue)](https://github.com/animvin777/snowflake_config_rules)

## 🎯 What This App Does

The Configuration Compliance Manager is a Snowflake Native Application that helps organizations maintain consistent configuration standards across their Snowflake environment. It provides:

### Core Capabilities

```
┌─────────────────────────────────────────────────────────────────┐
│                    Compliance Management Flow                    │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
  │   Define     │         │   Monitor    │         │  Remediate   │
  │    Rules     │────────>│  Compliance  │────────>│  Violations  │
  └──────────────┘         └──────────────┘         └──────────────┘
       │                          │                         │
       │                          │                         │
       v                          v                         v
  Apply custom            Real-time status         One-click fixes
  thresholds              dashboards               or bulk SQL
```

### Supported Compliance Areas

| Category | What It Monitors | Example Rules |
|----------|-----------------|---------------|
| **Warehouse Configuration** | Auto-suspend, statement timeouts, concurrency | Max auto-suspend ≤ 30 seconds |
| **Data Retention** | Time Travel retention on databases, schemas, tables | Max retention ≤ 1 day |
| **Tag Compliance** | Required tags on warehouses, databases, tables | "cost_center" tag must be present |
| **Whitelist Management** | Exception handling for valid violations | Allow specific warehouses to exceed limits |

---

## ✨ Key Features

### 1. Flexible Rule Configuration
- **Pre-built Rules**: 5 ready-to-use rules for common scenarios
- **Custom Thresholds**: Set your own compliance limits
- **Tag-Based Rules**: Apply different thresholds based on tag values
- **Quick Setup**: Apply all default rules with one click

### 2. Multi-Dimensional Compliance Monitoring
- **Warehouse Compliance**: Monitor auto-suspend, timeouts, sizing
- **Database Retention Compliance**: Track Time Travel settings across all objects
- **Tag Compliance**: Ensure mandatory tags are applied
- **Whitelist Management**: Handle approved exceptions gracefully

### 3. Automated Remediation
- **One-Click Fix**: Automatically remediate individual violations
- **Bulk SQL Generation**: Generate SQL for mass remediation
- **Preview Before Execute**: Review all changes before applying
- **Whitelist Violations**: Mark approved exceptions

### 4. Comprehensive Visibility
- **Compliance Dashboards**: Real-time status with metrics
- **Violation Details**: See exactly what's non-compliant and why
- **Execution History**: Track all remediation actions
- **Data Explorer**: Inspect all collected configuration data

### 5. Automated Data Collection
- **Scheduled Tasks**: Daily automated data gathering
- **Serverless Compute**: Cost-efficient managed tasks
- **Task Monitoring**: View execution history and status
- **Error Handling**: Graceful failure management

---

## 🚀 Quick Start

### Prerequisites

- Snowflake account with **ACCOUNTADMIN** privileges
- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) installed

### Installation (5 Minutes)

**Step 1: Clone the Repository**
```bash
git clone https://github.com/animvin777/snowflake_config_rules.git
cd snowflake_config_rules
```

**Step 2: Configure Snowflake CLI**
```bash
snow connection add
# Follow prompts to configure your Snowflake connection
```

**Step 3: Deploy the App**
```bash
snow app run
```

**Step 4: Grant Privileges**

When prompted, grant the following privileges:
- `CREATE WAREHOUSE` - Creates app compute warehouse
- `MANAGE WAREHOUSES` - Monitors and modifies warehouse configs
- `EXECUTE TASK` - Manages scheduled data collection tasks
- `EXECUTE MANAGED TASK` - Runs serverless tasks
- `IMPORTED PRIVILEGES ON SNOWFLAKE DB` - Accesses metadata views

**Step 5: Post-Installation Setup (Required)**

Create the parameter monitoring task in your account:

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE SNOWFLAKE_CONFIG_RULES_APP;

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

ALTER TASK data_schema.warehouse_params_monitor_task RESUME;
GRANT ALL ON TASK data_schema.warehouse_params_monitor_task TO APPLICATION SNOWFLAKE_CONFIG_RULES_APP;

-- Execute tasks to populate initial data
EXECUTE TASK data_schema.warehouse_monitor_task;
EXECUTE TASK data_schema.warehouse_params_monitor_task;
```

> **Why is this needed?** Snowflake Native Apps cannot directly execute `SHOW PARAMETERS FOR WAREHOUSE` due to security restrictions. This task runs with your account privileges to capture parameter values.

**Step 6: Apply Default Rules**

1. Open the app in Snowflake UI
2. Navigate to **Configure Rules** tab
3. Click **Apply Default Rules** button

✅ **You're all set!** The app is now monitoring your environment.

---

## 📊 Architecture

### High-Level Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Snowflake Account                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────┐         │
│  │      Configuration Compliance Manager (Native App)      │         │
│  ├─────────────────────────────────────────────────────────┤         │
│  │                                                         │         │
│  │  ┌──────────────┐    ┌─────────────┐   ┌────────────┐ │         │
│  │  │  Streamlit   │    │ Compliance  │   │  Database  │ │         │
│  │  │      UI      │◄───┤    Logic    │◄──┤   Layer    │ │         │
│  │  │  (8 Tabs)    │    │             │   │            │ │         │
│  │  └──────────────┘    └─────────────┘   └────────────┘ │         │
│  │         │                                      │       │         │
│  │         └──────────────────────────────────────┘       │         │
│  │                           │                            │         │
│  │         ┌─────────────────┴──────────────────┐         │         │
│  │         │        Data Schema (Tables)        │         │         │
│  │         ├────────────────────────────────────┤         │         │
│  │         │ • warehouse_details                │         │         │
│  │         │ • database_retention_details       │         │         │
│  │         │ • tag_compliance_details           │         │         │
│  │         │ • config_rules                     │         │         │
│  │         │ • applied_rules                    │         │         │
│  │         │ • applied_tag_rules                │         │         │
│  │         │ • rule_whitelist                   │         │         │
│  │         └────────────────────────────────────┘         │         │
│  │                           ▲                            │         │
│  │         ┌─────────────────┴──────────────────┐         │         │
│  │         │    Serverless Managed Tasks        │         │         │
│  │         ├────────────────────────────────────┤         │         │
│  │         │ • warehouse_monitor_task           │         │         │
│  │         │ • db_retention_monitor_task        │         │         │
│  │         │ • tag_monitor_task                 │         │         │
│  │         └────────────────────────────────────┘         │         │
│  └─────────────────────────────────────────────────────────┘         │
│                           ▲                                          │
│                           │                                          │
│  ┌────────────────────────┴──────────────────────┐                  │
│  │  Consumer-Created Task (Post-Install)         │                  │
│  │  • warehouse_params_monitor_task              │                  │
│  │    (Captures statement timeout parameters)    │                  │
│  └───────────────────────────────────────────────┘                  │
│                                                                       │
│  ┌───────────────────────────────────────────────┐                  │
│  │   Your Snowflake Objects (Monitored)          │                  │
│  ├───────────────────────────────────────────────┤                  │
│  │ • Warehouses                                  │                  │
│  │ • Databases, Schemas, Tables                  │                  │
│  │ • Tags                                        │                  │
│  └───────────────────────────────────────────────┘                  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
snowflake_config_rules/
├── snowflake.yml              # Snowflake CLI project configuration
├── README.md                  # This file (GitHub documentation)
├── app/
│   ├── manifest.yml          # Native App manifest (privileges, version)
│   ├── setup_script.sql      # Database schema initialization
│   ├── README.md             # User documentation (shown in app)
│   └── streamlit/            # Streamlit application
│       ├── app.py                    # Main entry point & routing
│       ├── database.py               # All database operations
│       ├── compliance.py             # Compliance checking logic
│       ├── ui_utils.py               # Shared UI components
│       ├── styles.css                # Custom CSS styling
│       ├── tab_rule_config.py        # Configure Rules tab
│       ├── tab_tag_compliance.py     # Tag Compliance tab
│       ├── tab_wh_compliance.py      # Warehouse Compliance tab
│       ├── tab_database_compliance.py # Database Compliance tab
│       ├── tab_task_management.py    # Task Management tab
│       ├── tab_whitelist.py          # Whitelist Management tab
│       ├── tab_query_data.py         # Data Explorer tab
│       └── tab_details.py            # App Details tab
├── scripts/
│   └── post_deploy.sql       # Post-deployment scripts
└── output/
    └── deploy/               # Build artifacts (generated)
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Interactive web UI |
| **Backend** | Snowflake SQL | Data processing & compliance checks |
| **Data Collection** | Snowflake Tasks | Automated scheduled jobs |
| **Deployment** | Snowflake CLI | Build & deployment automation |
| **Compute** | Serverless Managed Tasks | Cost-efficient execution |

---

## 🛠️ Development

### Local Development Setup

**Prerequisites:**
- Python 3.8+
- Snowflake CLI installed
- Access to a Snowflake account

**Steps:**

1. **Clone and configure**
   ```bash
   git clone https://github.com/animvin777/snowflake_config_rules.git
   cd snowflake_config_rules
   snow connection add
   ```

2. **Deploy to dev environment**
   ```bash
   snow app run
   ```

3. **Make changes**
   - Edit files in `app/streamlit/`
   - Modify database schema in `app/setup_script.sql`
   - Update manifest in `app/manifest.yml`

4. **Redeploy**
   ```bash
   snow app run
   ```

## 📖 Usage Guide

### Common Workflows

#### 1. Enforce Auto-Suspend Policy

```
Goal: Ensure all warehouses suspend within 30 seconds

Steps:
  1. Configure Rules → Apply "Max Auto Suspend" = 30
  2. Warehouse Compliance → Filter "Non-Compliant Only"
  3. Click "Fix" on each warehouse
  
Result: 40-60% reduction in idle compute costs
```

#### 2. Reduce Time Travel Storage Costs

```
Goal: Set 1-day retention across all tables

Steps:
  1. Configure Rules → Apply "Max Table Retention" = 1
  2. Database Compliance → Search database
  3. Click "Fix All Non-Compliant Tables"
  
Result: 85% reduction in storage costs
```

#### 3. Ensure Tag Compliance

```
Goal: Verify all warehouses have "cost_center" tag

Steps:
  1. Configure Rules → Add Tag Rule (cost_center, WAREHOUSE)
  2. Tag Compliance → Select "Warehouse" filter
  3. Review violations → Generate remediation SQL
  
Result: 100% tag coverage for cost allocation
```

---

## 🔒 Security & Compliance

### Data Privacy
- ✅ **Zero-day retention**: All app tables use 0-day retention
- ✅ **Metadata only**: No query results or PII collected
- ✅ **Read-only by default**: Fix actions require explicit user action

### Privilege Model

| Privilege | Why It's Needed | Scope |
|-----------|----------------|-------|
| `CREATE WAREHOUSE` | Create app's compute warehouse | One-time during install |
| `MANAGE WAREHOUSES` | Monitor configs & apply fixes | Ongoing for compliance |
| `EXECUTE TASK` | Create scheduled tasks | One-time task setup |
| `EXECUTE MANAGED TASK` | Run serverless tasks | Ongoing automated collection |
| `IMPORTED PRIVILEGES ON SNOWFLAKE DB` | Access ACCOUNT_USAGE views | Read-only metadata access |


## 🐛 Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No data showing | Tasks haven't run | Go to Task Management → Execute tasks manually |
| NULL parameter values | Post-install task not created | Run post-installation SQL from setup guide |
| Fix button fails | Missing MANAGE WAREHOUSES privilege | Re-grant privileges to app |
| High costs | Tasks using dedicated warehouse | Verify tasks use managed compute (serverless) |

### Diagnostic Queries

```sql
-- Check task execution
SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'data_schema.warehouse_monitor_task'
))
ORDER BY scheduled_time DESC
LIMIT 10;

-- Verify data collection
SELECT COUNT(*) as warehouse_count,
       MAX(capture_timestamp) as last_capture
FROM data_schema.warehouse_details;

-- Check granted privileges
SHOW GRANTS TO APPLICATION snowflake_config_rules_app;
```

---

## 📊 Performance & Cost

### Expected Costs

| Component | Compute | Frequency | Est. Monthly Cost |
|-----------|---------|-----------|-------------------|
| Warehouse monitor task | Serverless (XSMALL) | Daily | < $1 |
| DB retention task | Serverless (XSMALL) | Daily | < $1 |
| Tag monitor task | Serverless (XSMALL) | Daily | < $1 |
| Streamlit UI | XSMALL warehouse | On-demand | Negligible |
| **Total** | - | - | **< $5/month** |

### Cost Savings Potential

- **Auto-suspend optimization**: 40-60% reduction in idle costs
- **Retention optimization**: 85% reduction in storage costs
- **Serverless tasks**: 40-50% cheaper than dedicated warehouses

---

## 📋 Version History

| Version | Date | Changes |
|---------|------|---------|
| **2.3** | Nov 2025 | Whitelist management, tag compliance, improved UI |
| **2.2** | Nov 2025 | Apply default rules button, data explorer |
| **2.1** | Nov 2025 | Task execution history, dynamic discovery |
| **2.0** | Nov 2025 | Database retention rules, task management |
| **1.0** | Sep 2025 | Initial release |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Resources

- [Snowflake Native Apps Documentation](https://docs.snowflake.com/en/developer-guide/native-apps/native-apps-about)
- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Managed Tasks Guide](https://docs.snowflake.com/en/user-guide/tasks-managed)

---

**Last Updated:** November 17, 2025 | **Version:** 2.3
