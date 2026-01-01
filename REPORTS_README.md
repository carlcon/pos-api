# Report Generation System

## Overview

The POS system now uses an async report generation system with:
- **Django Backend** - API endpoints for report generation
- **Celery** - Background task processing for PDF generation
- **WeasyPrint** - Professional PDF generation from HTML templates
- **Redis** - Message broker for Celery tasks

## Architecture

```
Frontend (Next.js)
    ↓ POST /api/dashboard/reports/generate/
Backend (Django)
    ↓ Creates Celery task
Celery Worker
    ↓ Generates PDF with WeasyPrint
    ↓ Saves to media/reports/
Frontend polls /api/dashboard/reports/status/<task_id>/
    ↓ Downloads PDF when ready
```

## Running the System

### 1. Start Redis (Message Broker)

```bash
# macOS (with Homebrew)
brew services start redis

# Or run in foreground
redis-server
```

### 2. Start Celery Worker

```bash
cd pos-api
source venv/bin/activate
celery -A main worker -l info
```

### 3. Start Celery Beat (Optional - for scheduled tasks)

```bash
cd pos-api
source venv/bin/activate
celery -A main beat -l info
```

### 4. Start Django Server

```bash
cd pos-api
source venv/bin/activate
python manage.py runserver 8088
```

### 5. Start Next.js Frontend

```bash
cd pos-app
npm run dev
```

## API Endpoints

### Generate Report (Async)
```http
POST /api/dashboard/reports/generate/
Content-Type: application/json

{
  "report_type": "daily-sales",
  "format": "pdf",
  "store_id": 1  // optional
}

Response:
{
  "task_id": "abc-123-def-456",
  "status": "pending",
  "format": "pdf"
}
```

### Check Report Status
```http
GET /api/dashboard/reports/status/<task_id>/

Response (pending):
{
  "status": "pending",
  "message": "Task is waiting to start..."
}

Response (processing):
{
  "status": "processing",
  "message": "Generating PDF..."
}

Response (completed):
{
  "status": "completed",
  "file_url": "/media/reports/daily-sales_20260101_123456.pdf",
  "filename": "daily-sales_20260101_123456.pdf",
  "download_url": "/api/dashboard/reports/download/daily-sales_20260101_123456.pdf/"
}

Response (failed):
{
  "status": "failed",
  "error": "Error message here"
}
```

### Download Report
```http
GET /api/dashboard/reports/download/<filename>/

Response: PDF file download
```

### Legacy JSON Endpoints (for CSV export)
All existing report endpoints still work for CSV export:
```http
GET /api/dashboard/reports/daily-sales/?store_id=1
GET /api/dashboard/reports/inventory-valuation/?store_id=1
...etc
```

## Report Types

Available report types:
- `daily-sales` - Daily Sales Report
- `weekly-sales` - Weekly Sales Summary
- `monthly-revenue` - Monthly Revenue Analysis
- `payment-breakdown` - Payment Method Breakdown
- `stock-levels` - Stock Levels Report
- `low-stock` - Low Stock Alert Report
- `stock-movement` - Stock Movement History
- `inventory-valuation` - Inventory Valuation
- `top-selling` - Top Selling Products
- `products-by-category` - Products by Category
- `monthly-expenses` - Monthly Expenses Analysis
- `expenses-by-category` - Expenses by Category
- `expenses-by-vendor` - Expenses by Vendor
- `expense-transactions` - Expense Transactions

## PDF Template Customization

PDF reports are generated from HTML templates located in:
```
pos-api/dashboard/templates/reports/
├── base.html           # Base template with styling
└── generic_report.html # Generic report layout
```

To customize PDF appearance, edit these templates. WeasyPrint supports most CSS for print media.

## Celery Tasks

### Report Generation Task
```python
from dashboard.tasks import generate_report_pdf

task = generate_report_pdf.delay(
    report_type='daily-sales',
    report_data={...},
    partner_id=1,
    store_id=1
)
```

### Cleanup Task
Old reports (7+ days) are automatically cleaned up daily at 2:30 AM.

Manual cleanup:
```python
from dashboard.tasks import cleanup_old_reports
cleanup_old_reports.delay()
```

## Monitoring Celery

### View Active Tasks
```bash
celery -A main inspect active
```

### View Registered Tasks
```bash
celery -A main inspect registered
```

### Flower (Web-based monitoring)
```bash
pip install flower
celery -A main flower
# Visit http://localhost:5555
```

## Troubleshooting

### Reports not generating
1. Check Redis is running: `redis-cli ping` (should return "PONG")
2. Check Celery worker is running and connected
3. Check Django logs for errors
4. Check Celery worker logs for task failures

### PDF generation errors
1. Ensure WeasyPrint dependencies are installed:
   ```bash
   # macOS
   brew install cairo pango gdk-pixbuf libffi
   ```
2. Check template syntax in dashboard/templates/reports/
3. Check Celery worker logs for WeasyPrint errors

### Permission errors
1. Ensure media/reports/ directory exists and is writable
2. Check file permissions: `chmod 755 media/reports/`

## Performance Optimization

For production:
1. Use multiple Celery workers for parallel processing:
   ```bash
   celery -A main worker -l info --concurrency=4
   ```

2. Use a production-ready message broker (RabbitMQ instead of Redis)

3. Configure result backend for task result persistence:
   ```python
   # settings.py
   CELERY_RESULT_BACKEND = 'django-db'
   ```

4. Set task expiration to clean up old results:
   ```python
   CELERY_TASK_RESULT_EXPIRES = 3600  # 1 hour
   ```
