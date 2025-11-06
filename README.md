# Snowflake Config Rules

A Snowflake Native App for defining, applying, and enforcing configuration compliance rules across all warehouses in your Snowflake account.

[![Snowflake](https://img.shields.io/badge/Snowflake-Native%20App-blue)](https://www.snowflake.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Overview

Snowflake Config Rules helps you maintain consistent warehouse configurations across your Snowflake account by:
- Defining reusable configuration rules
- Monitoring compliance in real-time
- Automatically generating remediation SQL
- Providing a visual dashboard for compliance status

## ✨ Key Features

### 📋 Rule Configuration
- View all available configuration rules
- Apply rules with custom threshold values
- Manage currently applied rules
- Generate SQL to fix all non-compliant warehouses for a specific rule
- Deactivate rules when no longer needed

### 🔍 Compliance View
- Real-time compliance status for all warehouses
- Summary metrics (Total, Compliant, Non-Compliant warehouses)
- Filter views: All Warehouses, Non-Compliant Only, or Compliant Only
- **Fix Button** - Execute remediation with one click:
  - Runs fix SQL automatically
  - Updates warehouse_details table with new values
  - Shows "Configuration Updated" on success
  - Displays detailed error messages on failure
- Toggle between Tile View and List View
- Detailed violation information for each warehouse

### 📊 Warehouse Overview
- Complete inventory of all warehouses
- Key metrics dashboard
- Visual analytics showing warehouse distribution by size, type, and owner
- Detailed warehouse configurations with expandable sections
- Auto-suspend distribution charts

### 🎨 Modern UI
- Minimalistic, clean design
- Refresh button on top right of all tabs
- External CSS for easy customization
- Responsive layout with styled cards
- Color-coded compliance status

## 🏗️ Architecture

### Modular Code Structure

The application is built with a modular architecture for maintainability and extensibility:

```
app/streamlit/
├── app.py                      # Main entry point
├── database.py                 # Database operations
├── compliance.py               # Compliance checking logic
├── ui_utils.py                 # Reusable UI components
├── tab_rule_config.py         # Rule Configuration tab
├── tab_compliance.py          # Compliance View tab
├── tab_warehouse_overview.py  # Warehouse Overview tab
└── styles.css                 # External styling
```

**Benefits:**
- ✅ Separation of concerns
- ✅ Easy to maintain and extend
- ✅ Reusable components
- ✅ Independent module testing
- ✅ Clear code organization

### Database Schema

**`data_schema.warehouse_details`**
- Stores current warehouse configurations captured from `SHOW WAREHOUSES`
- Updated every 2 hours by the monitoring task
- Captures: name, type, size, auto_suspend, statement_timeout, cluster settings, etc.

**`data_schema.config_rules`**
- Stores available configuration rules that can be applied
- Pre-populated with two rules (Max Statement Timeout, Max Auto Suspend)
- Extensible - add new rules via INSERT statements

**`data_schema.applied_rules`**
- Stores rules that have been applied with their threshold values
- Tracks when rules were applied and by whom
- Supports rule versioning (deactivating old rules when new thresholds are set)

## 🚀 Quick Start

### Installation

1. **Deploy the app** to your Snowflake account:
   ```bash
   snow app run
   ```

2. **Grant required privileges** (automatically requested during installation):
   - CREATE WAREHOUSE
   - EXECUTE TASK
   - MANAGE WAREHOUSES
   - EXECUTE MANAGED TASK
   - MODIFY (to alter warehouse configurations)

### First Steps

1. **Open the Streamlit app** from Snowflake
2. **Navigate to Rule Configuration tab**
3. **Apply your first rule:**
   - Select "Max Auto Suspend in Seconds"
   - Enter threshold: `300` (5 minutes)
   - Click **Apply Rule**
4. **Check compliance:**
   - Go to **Compliance View** tab
   - Review non-compliant warehouses
   - Click **Fix** button to remediate automatically

## 📚 Built-in Configuration Rules

### 1. Max Statement Timeout in Seconds
- **Purpose**: Ensures warehouses don't have statement timeouts exceeding your standards
- **Parameter**: `STATEMENT_TIMEOUT_IN_SECONDS`
- **Operator**: MAX (warehouse value must be ≤ threshold)
- **Example**: Set threshold to 600 seconds (10 minutes)

### 2. Max Auto Suspend in Seconds
- **Purpose**: Prevents warehouses from staying idle too long, reducing compute costs
- **Parameter**: `AUTO_SUSPEND`
- **Operator**: MAX (warehouse value must be ≤ threshold)
- **Example**: Set threshold to 300 seconds (5 minutes)

## 🔧 Usage Guide

### Applying Configuration Rules

1. Navigate to the **Rule Configuration** tab
2. Select a rule from the dropdown
3. Enter your desired threshold value
4. Click **Apply Rule**
5. The rule is now active and monitoring begins

### Monitoring Compliance

1. Go to the **Compliance View** tab
2. Review the summary metrics at the top
3. Use filters to focus on specific warehouse sets
4. Toggle between Tile and List views
5. For each non-compliant warehouse, you'll see:
   - Current configuration value
   - Required threshold value
   - Specific violations

### Fixing Non-Compliant Warehouses

**Automatic Fix (Recommended):**
1. In the **Compliance View** tab
2. Find a non-compliant warehouse
3. Click **Fix** button
4. The app will:
   - Execute ALTER WAREHOUSE SQL
   - Update the warehouse_details table
   - Show "Configuration Updated" on success
   - Display error details if it fails

**Manual Fix (Alternative):**
1. In the **Rule Configuration** tab
2. Find the applied rule
3. Click **Generate SQL**
4. Copy and execute the generated SQL manually

### Example Remediation SQL

```sql
-- Generated SQL to fix auto_suspend violations
ALTER WAREHOUSE COMPUTE_WH
SET AUTO_SUSPEND = 300;

ALTER WAREHOUSE DATA_LOAD_WH
SET AUTO_SUSPEND = 300;
```

## 🔌 Extending with Custom Rules

### Adding a New Rule (Simple)

For parameters already captured (like `AUTO_SUSPEND`, `STATEMENT_TIMEOUT_IN_SECONDS`, `SIZE`):

```sql
USE APPLICATION snowflake_config_rules_app;

INSERT INTO data_schema.config_rules (
    rule_id, 
    rule_name, 
    rule_description, 
    warehouse_parameter, 
    comparison_operator, 
    unit
)
VALUES (
    'MIN_AUTO_SUSPEND',
    'Min Auto Suspend in Seconds',
    'Minimum required auto suspend time to prevent rapid cycling',
    'AUTO_SUSPEND',
    'MIN',
    'seconds'
);
```

✅ **That's it!** The app will automatically:
- Show the new rule in Rule Configuration tab
- Check compliance when applied
- Generate appropriate SQL to fix violations

### Supported Comparison Operators

- **MAX**: Warehouse value must be ≤ threshold
- **MIN**: Warehouse value must be ≥ threshold
- **EQUALS**: Warehouse value must exactly match threshold

### Parameters Already Available

These parameters are already captured and can be used immediately:
- `AUTO_SUSPEND`
- `STATEMENT_TIMEOUT_IN_SECONDS`
- `SIZE`
- `TYPE`
- `MIN_CLUSTER_COUNT`
- `MAX_CLUSTER_COUNT`
- `SCALING_POLICY`
- `MAX_CONCURRENCY_LEVEL`
- `STATEMENT_QUEUED_TIMEOUT_IN_SECONDS`

### Adding Custom Parameters

For new parameters not captured by default:

1. **Update `setup_script.sql`** to capture the parameter in `warehouse_details` table
2. **Insert the rule definition** as shown above
3. **Update `compliance.py`** in the `check_compliance()` function:
   ```python
   elif param == 'YOUR_PARAMETER':
       wh_value = wh['YOUR_PARAMETER']
   ```
4. **Update `compliance.py`** in the `generate_fix_sql()` function:
   ```python
   elif parameter == 'YOUR_PARAMETER':
       return f"ALTER WAREHOUSE {warehouse_name}\nSET YOUR_PARAMETER = {threshold_value};"
   ```

For detailed guidance, see the [Adding New Rules Guide](#adding-new-rules-detailed).

## 📅 Data Collection Schedule

The app runs a scheduled task to capture warehouse configurations:
- **Frequency**: Every 2 hours (customizable in setup_script.sql)
- **Initial Run**: Executed immediately during installation
- **Manual Refresh**: Click the 🔄 button in the top right of any tab

## 🛠️ Development

### Module Descriptions

**`database.py`** - Database operations
- Query execution
- CRUD operations
- Warehouse details updates after fixes

**`compliance.py`** - Compliance logic
- Warehouse validation against rules
- SQL generation for remediation

**`ui_utils.py`** - UI components
- CSS loading
- Header/footer rendering
- Common UI elements

**`tab_*.py`** - Tab implementations
- Each tab is a self-contained module
- Easy to add new tabs

**`styles.css`** - Styling
- Minimalistic design
- Metric cards, warehouse cards
- Color-coded status indicators

### Adding a New Tab

1. Create `tab_your_feature.py`
2. Implement `render_your_feature_tab(session)`
3. Import in `app.py`
4. Add to tabs list: `st.tabs([..., "Your Feature"])`
5. Call render function: `render_your_feature_tab(session)`

## 🔍 Troubleshooting

### No warehouse data showing in the app
**Solution**: Wait for the monitoring task to run (every 2 hours), or manually execute:
```sql
EXECUTE TASK data_schema.warehouse_monitor_task;
```

### Statement timeout rule shows NULL values
**Solution**: The optional parameter monitoring task needs to be set up. See the [Post-Installation Setup](#post-installation-setup-optional) section in the detailed README.

### Cannot apply rules
**Solution**: Ensure the app has been granted the MODIFY privilege.

### Fix button doesn't work
**Solution**: 
- Check error message displayed in the card
- Ensure you have MODIFY privilege on the warehouse
- Verify the warehouse exists and is accessible

### Generated SQL doesn't work
**Solution**: Ensure you're running the SQL with a role that has MODIFY privilege on the warehouses.

## 📖 Best Practices

1. **Start with Higher Thresholds**: Begin with lenient thresholds and gradually tighten them
2. **Test on Non-Production First**: Apply rules to dev/test warehouses before production
3. **Monitor Trends**: Use the Warehouse Overview tab to understand current configurations
4. **Regular Reviews**: Periodically review and update rule thresholds based on actual usage
5. **Document Exceptions**: If certain warehouses need different settings, document why
6. **Use Refresh Button**: Click refresh after making manual changes to see updated compliance status

## 🔒 Security

- All data is stored with 0-day retention for compliance
- The app requests only necessary privileges
- Consumer controls which rules to apply and when
- Fix button executes SQL with consumer's privileges
- Manual SQL generation is read-only; consumer must approve execution

## 📋 Version History

- **v1.2.0**: 
  - Added automatic Fix button in Compliance View
  - Modular code structure
  - Refresh button in all tabs
  - Minimalistic UI redesign
  - External CSS file
- **v1.1.0**: 
  - Added Tile/List view toggle
  - Enhanced warehouse details
  - Improved SQL generation
- **v1.0.0**: 
  - Initial release with Max Statement Timeout and Max Auto Suspend rules

## 🤝 Contributing

To extend this app:
1. Fork the repository
2. Create a feature branch
3. Make your changes following the modular structure
4. Test thoroughly
5. Submit a pull request with detailed description

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Contact your Snowflake account team
- Refer to [Snowflake Native App documentation](https://docs.snowflake.com/en/developer-guide/native-apps/native-apps-about)

---

## 📚 Appendix

### Adding New Rules (Detailed)

#### Example 1: Min Auto Suspend Rule

```sql
INSERT INTO data_schema.config_rules (
    rule_id, rule_name, rule_description, 
    warehouse_parameter, comparison_operator, unit
)
VALUES (
    'MIN_AUTO_SUSPEND',
    'Min Auto Suspend in Seconds',
    'Minimum required auto suspend time to prevent rapid cycling',
    'AUTO_SUSPEND', 'MIN', 'seconds'
);
```

#### Example 2: Max Warehouse Size Rule

```sql
INSERT INTO data_schema.config_rules (
    rule_id, rule_name, rule_description,
    warehouse_parameter, comparison_operator, unit
)
VALUES (
    'MAX_WAREHOUSE_SIZE',
    'Max Warehouse Size',
    'Restrict warehouse sizes to control costs',
    'SIZE', 'MAX', 'size_level'
);
```

#### Rule Definition Fields

| Field | Description | Example |
|-------|-------------|---------|
| `rule_id` | Unique identifier (uppercase, underscores) | `MAX_AUTO_SUSPEND` |
| `rule_name` | Display name shown in UI | `Max Auto Suspend in Seconds` |
| `rule_description` | Explanation of the rule's purpose | `Maximum allowed auto suspend time...` |
| `warehouse_parameter` | Warehouse parameter to check | `AUTO_SUSPEND` |
| `comparison_operator` | How to compare: MAX, MIN, or EQUALS | `MAX` |
| `unit` | Display unit for the threshold | `seconds` |

### Post-Installation Setup (Optional)

To capture additional warehouse parameters like `statement_timeout_in_seconds`, create a task in your account:

```sql
USE ROLE ACCOUNTADMIN;
USE DATABASE YOUR_DATABASE;

CREATE OR REPLACE TASK warehouse_params_monitor_task
    WAREHOUSE = YOUR_WAREHOUSE
    SCHEDULE = 'USING CRON 10 */2 * * * America/New_York'
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
      SHOW PARAMETERS IN WAREHOUSE IDENTIFIER(:wh_name);
      
      MERGE INTO snowflake_config_rules_app.data_schema.warehouse_details tgt
      USING (
        SELECT 
          :wh_name as warehouse_name,
          MAX(CASE WHEN "key" = 'STATEMENT_TIMEOUT_IN_SECONDS' 
              THEN TRY_CAST("value" AS NUMBER) END) as stmt_timeout
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
      ) src
      ON tgt.name = src.warehouse_name 
      WHEN MATCHED THEN UPDATE SET
        tgt.statement_timeout_in_seconds = src.stmt_timeout;
    EXCEPTION
      WHEN OTHER THEN CONTINUE;
    END;
  END FOR;
END;

ALTER TASK warehouse_params_monitor_task RESUME;
```

This enables monitoring of statement timeout values across warehouses.

---

**Built with ❄️ by the Snowflake Community**
