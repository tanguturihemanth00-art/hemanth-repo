"""
services/reporting_service.py
=============================
Generates a standalone HTML dashboard report from an ExecutionResult.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config.environment import get_env
from framework.core.logger import get_logger
from models.execution_result import ExecutionResult

_log = get_logger()

# Standard CSS using glassmorphism and modern styling
_CSS = """
:root {
    --bg-color: #0f172a;
    --text-color: #f8fafc;
    --card-bg: rgba(30, 41, 59, 0.7);
    --border-color: rgba(255, 255, 255, 0.1);
    --success-color: #10b981;
    --error-color: #ef4444;
    --skip-color: #f59e0b;
    --accent-color: #3b82f6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    padding: 2rem;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
}
header {
    margin-bottom: 2rem;
    text-align: center;
}
h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    background: linear-gradient(to right, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.subtitle {
    color: #94a3b8;
    font-size: 1.1rem;
}
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
}
.metric-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s;
}
.metric-card:hover {
    transform: translateY(-5px);
}
.metric-title {
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #cbd5e1;
    margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 2.5rem;
    font-weight: bold;
}
.success { color: var(--success-color); }
.error { color: var(--error-color); }
.skip { color: var(--skip-color); }

table {
    width: 100%;
    border-collapse: collapse;
    background: var(--card-bg);
    border-radius: 12px;
    overflow: hidden;
    backdrop-filter: blur(10px);
    border: 1px solid var(--border-color);
}
th, td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}
th {
    background: rgba(0, 0, 0, 0.2);
    font-weight: 600;
    color: #e2e8f0;
}
tr:last-child td {
    border-bottom: none;
}
tr:hover {
    background: rgba(255, 255, 255, 0.05);
}
.badge {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
}
.badge-SUCCESS { background: rgba(16, 185, 129, 0.2); color: var(--success-color); border: 1px solid rgba(16, 185, 129, 0.5); }
.badge-FAILURE { background: rgba(239, 68, 68, 0.2); color: var(--error-color); border: 1px solid rgba(239, 68, 68, 0.5); }
.badge-SKIPPED { background: rgba(245, 158, 11, 0.2); color: var(--skip-color); border: 1px solid rgba(245, 158, 11, 0.5); }
.screenshot-link {
    color: var(--accent-color);
    text-decoration: none;
}
.screenshot-link:hover {
    text-decoration: underline;
}
"""

class ReportingService:
    """Service to generate HTML execution reports."""

    @classmethod
    def generate_html_report(cls, result: ExecutionResult) -> Path:
        """
        Generates a standalone HTML dashboard report and saves it to the REPORT_DIR.
        
        Args:
            result: The finalized ExecutionResult object.
            
        Returns:
            Path to the generated HTML report file.
        """
        _log.info(f"Generating HTML report for execution: {result.execution_id}")
        env = get_env()
        
        # Calculate rates
        total = result.total_rows
        success_rate = (result.success_count / total * 100) if total > 0 else 0
        
        # Format the start time
        start_time_str = result.started_at.strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract dynamic columns from the first row's raw_data (excluding internal fields)
        internal_fields = {'row_id', 'status', 'error_message', 'processed_at', 'screenshot_path', 'row_index_'}
        dynamic_cols = []
        if result.row_results and result.row_results[0].raw_data:
            dynamic_cols = [k for k in result.row_results[0].raw_data.keys() if k not in internal_fields]

        # Build table headers
        headers_html = "<th>Row ID</th>"
        for col in dynamic_cols:
            headers_html += f"<th>{col.replace('_', ' ').title()}</th>"
        headers_html += "<th>Status</th><th>Duration</th><th>Error Message</th><th>Screenshot</th>"

        # Build table rows
        table_rows_html = ""
        for row in result.row_results:
            error_msg = row.error_message or "-"
            
            screenshot_cell = "-"
            if row.screenshot_path:
                filename = Path(row.screenshot_path).name
                screenshot_cell = f'<a href="./screenshots/{filename}" class="screenshot-link" target="_blank">View</a>'
            
            # Start with Row ID
            row_html = f"<td>{row.row_id}</td>"
            
            # Add dynamic columns
            for col in dynamic_cols:
                val = row.raw_data.get(col, "-")
                row_html += f"<td>{val}</td>"
                
            # Add standard columns
            row_html += f"""
                <td><span class="badge badge-{row.status}">{row.status}</span></td>
                <td>{row.duration_seconds:.2f}s</td>
                <td>{error_msg}</td>
                <td>{screenshot_cell}</td>
            """
            
            table_rows_html += f"<tr>{row_html}</tr>"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Execution Report - {result.workflow_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>{_CSS}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Enterprise Automation Dashboard</h1>
            <p class="subtitle">Workflow: <strong>{result.workflow_name}</strong> | Started: {start_time_str} | Duration: {result.duration_seconds:.2f}s</p>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Total Records</div>
                <div class="metric-value">{result.total_rows}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Success Rate</div>
                <div class="metric-value success">{success_rate:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Successful</div>
                <div class="metric-value success">{result.success_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Failed</div>
                <div class="metric-value error">{result.failure_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Skipped</div>
                <div class="metric-value skip">{result.skipped_count}</div>
            </div>
        </div>

        <div style="overflow-x: auto; width: 100%;">
            <table>
                <thead>
                    <tr>
                        {headers_html}
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        
        report_file = env.report_dir / f"index.html"
        report_file.write_text(html_content, encoding="utf-8")
        _log.info(f"HTML report saved to: {report_file}")
        
        # Save a metadata json for CI/CD integrations
        metadata_file = env.report_dir / "summary.json"
        metadata_file.write_text(json.dumps(result.summary(), indent=2), encoding="utf-8")
        
        return report_file
