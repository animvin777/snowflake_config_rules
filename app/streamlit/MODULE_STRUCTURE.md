# Snowflake Config Rules - Modular Structure

## File Organization

The application has been refactored into a modular structure for better maintainability and code organization.

### Main Application
- **`app.py`** - Main Streamlit application entry point
  - Initializes Streamlit configuration
  - Gets Snowflake session
  - Loads CSS and renders UI components
  - Orchestrates the three tabs

### Core Modules

#### `database.py`
**Purpose:** Database operations and queries
- `get_config_rules()` - Fetch configuration rules
- `get_applied_rules()` - Fetch active applied rules
- `get_warehouse_details()` - Fetch warehouse information
- `apply_rule()` - Apply a rule with threshold
- `deactivate_applied_rule()` - Deactivate a rule
- `execute_fix_sql()` - Execute remediation SQL

#### `compliance.py`
**Purpose:** Compliance checking logic
- `check_compliance()` - Validate warehouses against rules
- `generate_fix_sql()` - Generate ALTER WAREHOUSE statements

#### `ui_utils.py`
**Purpose:** Reusable UI components
- `load_css()` - Load external CSS file
- `render_header()` - Render main app header
- `render_footer()` - Render footer with timestamp
- `render_refresh_button()` - Render refresh button in tabs
- `render_metric_card()` - Render metric cards

### Tab Modules

#### `tab_rule_config.py`
**Purpose:** Rule Configuration tab
- Display available rules
- Apply new rules with thresholds
- Manage applied rules
- Generate SQL for non-compliant warehouses

#### `tab_compliance.py`
**Purpose:** Compliance View tab
- Display compliance metrics
- Show compliant/non-compliant warehouses
- Tile view and List view modes
- Fix button to remediate violations

#### `tab_warehouse_overview.py`
**Purpose:** Warehouse Overview tab
- Key metrics dashboard
- Detailed warehouse information
- Summary table
- Distribution analytics and charts

### Supporting Files
- **`styles.css`** - External CSS styling
- **`app_old.py`** - Backup of original monolithic app

## Benefits of Modular Structure

1. **Separation of Concerns** - Each module has a clear, single responsibility
2. **Maintainability** - Easier to locate and modify specific functionality
3. **Reusability** - Functions can be imported and reused across modules
4. **Testability** - Individual modules can be tested independently
5. **Readability** - Smaller, focused files are easier to understand
6. **Scalability** - New features can be added as new modules

## Import Structure

```
app.py (main entry point)
├── ui_utils (UI components)
├── tab_rule_config (Tab 1)
│   ├── database (data operations)
│   ├── compliance (compliance logic)
│   └── ui_utils (UI components)
├── tab_compliance (Tab 2)
│   ├── database (data operations)
│   ├── compliance (compliance logic)
│   └── ui_utils (UI components)
└── tab_warehouse_overview (Tab 3)
    ├── database (data operations)
    └── ui_utils (UI components)
```

## Development Guidelines

1. **Database Operations** - Add new queries to `database.py`
2. **Compliance Logic** - Add new compliance checks to `compliance.py`
3. **UI Components** - Add reusable components to `ui_utils.py`
4. **New Tabs** - Create new `tab_*.py` files following the pattern
5. **Styling** - Update `styles.css` for visual changes

## Running the Application

The application runs the same way as before:
```bash
snow app run
```

The Snowflake CLI will execute `app.py` as the main Streamlit entry point.
