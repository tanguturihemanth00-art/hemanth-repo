# Enterprise Automation Framework

A production-grade Python Playwright automation framework for business workflow automation.

---

## Architecture

```
project_root/
├── config/               # Config layer (YAML + env + constants)
├── framework/
│   ├── browser/          # Browser lifecycle, session management
│   ├── core/             # Logger, retry, exceptions, wait utils, context
│   └── reporting/        # Screenshots, JSON + Excel reports
├── pages/                # Page Object Model (BasePage + per-page classes)
├── services/             # Business-logic services (auth, excel, nav, validation)
├── workflows/            # Workflow orchestrators (extend BaseWorkflow)
├── models/               # Pydantic data models
├── data/
│   ├── input/            # Place your input Excel files here
│   ├── output/           # Auto-generated output (do not commit)
│   ├── failed/           # Failed rows saved separately
│   ├── screenshots/      # Failure/success screenshots
│   ├── logs/             # Rotating log files
│   └── session/          # Browser session state (auto-managed)
├── .env                  # ⚠️  Secrets — NEVER commit
├── .env.example          # Safe template — commit this
├── bootstrap.py          # Pre-flight health checks
├── main.py               # CLI entry point
└── requirements.txt
```

---

## Quick Start

### 1. Set Up Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` with your actual credentials:

```env
APP_URL=https://your-business-website.com
APP_USERNAME=your_fr_code_or_username
APP_PASSWORD=your_password
BROWSER_HEADLESS=false
```

### 4. Run Bootstrap Check

```bash
python bootstrap.py
```

### 5. Run a Workflow

```bash
python main.py --input data/input/records.xlsx --workflow your_workflow_name
```

---

## Building Your First Workflow

### Step 1 — Define Your Excel Record Model

```python
# models/your_record.py
from models.excel_record import ExcelRecord

class CustomerRecord(ExcelRecord):
    customer_id: str
    customer_name: str
    email: str
    category: str
```

### Step 2 — Implement the Login Page Locators

Open `pages/login_page.py` and replace the placeholder locators with real ones from your website:

```python
@property
def _username_input(self):
    return self.page.get_by_label("FR Code")   # ← your actual selector

@property
def _password_input(self):
    return self.page.get_by_label("Password")  # ← your actual selector

@property
def _login_button(self):
    return self.page.get_by_role("button", name="Login")  # ← your actual selector
```

### Step 3 — Create Your Workflow Page

```python
# pages/customer_creation_page.py
from pages.workflow_page import WorkflowPage

class CustomerCreationPage(WorkflowPage):
    async def fill_form(self, record: CustomerRecord):
        await self.safe_fill(self.page.get_by_label("Name"), record.customer_name)
        await self.safe_fill(self.page.get_by_label("Email"), record.email)

    async def submit_form(self):
        await self.safe_click(self.page.get_by_role("button", name="Save"))
        await self.wait_for_network_idle()
```

### Step 4 — Create Your Workflow

```python
# workflows/customer_creation.py
from workflows.base_workflow import BaseWorkflow
from models.your_record import CustomerRecord
from pages.customer_creation_page import CustomerCreationPage

class CustomerCreationWorkflow(BaseWorkflow[CustomerRecord]):

    @property
    def record_class(self):
        return CustomerRecord

    @property
    def workflow_name(self):
        return "customer_creation"

    async def process_row(self, page, record):
        form = CustomerCreationPage(page)
        await form.process_record(record, success_text="Saved successfully")
```

### Step 5 — Register in main.py

```python
from workflows.customer_creation import CustomerCreationWorkflow

registry = {
    "customer_creation": CustomerCreationWorkflow,
}
```

### Step 6 — Run It

```bash
python main.py --input data/input/customers.xlsx --workflow customer_creation
```

---

## Configuration Reference

| Setting | .env Key | Default | Description |
|---|---|---|---|
| App URL | `APP_URL` | — | Target website URL |
| Username / FR Code | `APP_USERNAME` | — | Login credential |
| Password | `APP_PASSWORD` | — | Login credential |
| Browser mode | `BROWSER_HEADLESS` | `false` | `true` for server runs |
| Session reuse | `SESSION_REUSE` | `true` | Skip login if session exists |
| Log level | `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING |
| Continue on failure | config.yaml | `true` | Process remaining rows after a failure |

---

## Output Files

After each run you will find:

| Path | Contents |
|---|---|
| `data/output/` | Full results Excel with status per row |
| `data/failed/` | Only failed rows (for re-processing) |
| `data/screenshots/` | Screenshots on failure/success |
| `data/logs/` | Rotating daily log files |
| `data/session/` | Saved browser session (auto-managed) |

---

## Locator Priority (enforced framework-wide)

1. `get_by_role()` — semantic and most stable
2. `get_by_label()` — form fields
3. `[data-testid='...']` — when explicitly set
4. CSS selector — specific and readable
5. XPath — **last resort only**

---

## Tech Stack

| Library | Purpose |
|---|---|
| `playwright` | Browser automation |
| `pandas` + `openpyxl` | Excel read/write |
| `pydantic` | Data validation |
| `python-dotenv` | `.env` loading |
| `PyYAML` | Config file |
| `loguru` | Structured logging |
| `tenacity` | Retry with backoff |
