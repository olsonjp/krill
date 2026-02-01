# Reports App

The Reports app provides comprehensive reporting functionality for the Krill system, including report generation, alert management, issue tracking, and sample search capabilities.

## Features

### 1. Report Generation
- **Report Templates**: Predefined templates for common report types
- **Multiple Formats**: Support for PDF, Excel, CSV, and JSON output
- **Parameterized Reports**: Customizable report parameters
- **Scheduled Reports**: Automated report generation on schedule

### 2. Alert System
- **System Alerts**: Monitor and manage system alerts
- **Severity Levels**: Low, Medium, High, and Critical alert levels
- **Alert Types**: Categorize alerts by type (storage, temperature, etc.)
- **Workflow Management**: Acknowledge and resolve alerts

### 3. Issue Tracking
- **Issue Reporting**: Report bugs, feature requests, and maintenance issues
- **Priority Management**: Low, Medium, High, and Urgent priority levels
- **Assignment System**: Assign issues to team members
- **Status Tracking**: Track issue progress from open to resolved

### 4. Sample Search
- **Advanced Search**: Search samples by name, type, and disposition
- **Filtering**: Multiple filter options for refined results
- **Export Results**: Download search results in various formats
- **Real-time Updates**: Live search with debouncing

### 5. Storage Dashboard
- **Capacity Monitoring**: Track storage usage and availability
- **Device Status**: Monitor storage device health and status
- **Statistics**: Comprehensive storage statistics and metrics

## Models

### ReportTemplate
- Defines report structure and configuration
- Supports multiple report types (sample inventory, storage capacity, etc.)
- JSON-based template configuration

### Report
- Generated report instances
- Tracks generation status and results
- Supports multiple output formats

### Alert
- System alerts and notifications
- Configurable severity and status levels
- Target-specific alerts (freezer, sample, etc.)

### Issue
- Issue tracking and management
- Priority and status management
- Assignment and resolution tracking

### ScheduledReport
- Automated report generation
- Configurable frequency and recipients
- Parameter management for scheduled reports

## API Endpoints

### Dashboard Statistics
- `GET /reports/dashboard/stats/` - Enhanced dashboard statistics

### Report Generation
- `POST /reports/generate/` - Generate new report
- `GET /reports/list/` - List user reports
- `GET /reports/detail/<id>/` - View report details
- `GET /reports/download/<id>/` - Download generated report

### Alert Management
- `GET /reports/alerts/` - List all alerts
- `POST /reports/alerts/create/` - Create new alert
- `POST /reports/alerts/<id>/acknowledge/` - Acknowledge alert
- `POST /reports/alerts/<id>/resolve/` - Resolve alert

### Issue Tracking
- `GET /reports/issues/` - List all issues
- `POST /reports/issues/report/` - Report new issue

### Sample Search
- `GET /reports/samples/search/` - Search samples with filters

### Storage Dashboard
- `GET /reports/storage/dashboard/` - Storage overview statistics

## Usage

### Generating Reports
1. Navigate to Reports Dashboard
2. Click "Generate Report"
3. Select template and configure parameters
4. Choose output format
5. Submit for generation

### Managing Alerts
1. View active alerts in the Alerts section
2. Acknowledge alerts when reviewed
3. Resolve alerts when issues are fixed
4. Create new alerts for system issues

### Reporting Issues
1. Use the Issue Tracking section
2. Fill out issue details and priority
3. Assign to team members if needed
4. Track resolution progress

### Searching Samples
1. Use the Sample Search interface
2. Enter search criteria and filters
3. View results with pagination
4. Export results as needed

## Configuration

### Report Templates
Configure report templates in the Django admin:
- Define report structure and parameters
- Set output format options
- Configure access permissions

### Alert Rules
Set up alert rules for:
- Storage capacity thresholds
- Temperature monitoring
- System performance metrics
- User activity monitoring

### Scheduled Reports
Configure automated reports for:
- Daily/weekly/monthly summaries
- Regulatory compliance reports
- Performance monitoring
- Data archiving

## Dependencies

- Django 5.0+
- Python 3.10+
- SQLite/PostgreSQL/MySQL database
- Material Icons for UI elements

## Installation

1. Add `reports` to `INSTALLED_APPS` in Django settings
2. Run migrations: `python manage.py migrate`
3. Include reports URLs in main URL configuration
4. Access via `/reports/` URL path

## Customization

### Adding New Report Types
1. Extend the `ReportTemplate` model choices
2. Create custom report generation logic
3. Add template configuration options
4. Update admin interface

### Custom Alert Types
1. Define new alert types in the Alert model
2. Create alert generation logic
3. Configure alert rules and thresholds
4. Add custom alert handling

### Extended Search
1. Add new search fields to Sample model
2. Extend search form and logic
3. Update search results display
4. Add export functionality

## Contributing

1. Follow Django coding standards
2. Add tests for new functionality
3. Update documentation
4. Submit pull requests

## License

This app is part of the Krill system and follows the same licensing terms.
