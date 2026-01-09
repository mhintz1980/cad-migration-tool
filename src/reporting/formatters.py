"""
Report formatters for different output formats.

Supports text, HTML, and JSON output.
"""

import json
from pathlib import Path
from typing import Protocol
from .report_generator import MigrationReport


class ReportFormatter(Protocol):
    """Protocol for report formatters."""

    def format(self, report: MigrationReport) -> str:
        """Format report to string."""
        ...

    def save(self, report: MigrationReport, output_path: Path):
        """Save formatted report to file."""
        ...


class TextFormatter:
    """Plain text report formatter."""

    def format(self, report: MigrationReport) -> str:
        """Format report as plain text."""
        return str(report)

    def save(self, report: MigrationReport, output_path: Path):
        """Save text report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(self.format(report))


class HTMLFormatter:
    """HTML report formatter."""

    def format(self, report: MigrationReport) -> str:
        """Format report as HTML."""
        failed_files = [f for f in report.file_results if f.status == "FAILED"]

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Migration Report: {report.migration_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .success {{ color: green; }}
        .failed {{ color: red; }}
        .pending {{ color: orange; }}
    </style>
</head>
<body>
    <h1>Migration Report: {report.migration_id}</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Profile:</strong> {report.profile}</p>
        <p><strong>Started:</strong> {report.started_at}</p>
        <p><strong>Completed:</strong> {report.completed_at or 'In progress'}</p>
        <p><strong>Duration:</strong> {report.duration:.1f}s</p>
        <p><strong>Total files:</strong> {report.total_files}</p>
        <p><strong>Successful:</strong> <span class="success">{report.successful}</span></p>
        <p><strong>Failed:</strong> <span class="failed">{report.failed}</span></p>
        <p><strong>Pending:</strong> <span class="pending">{report.pending}</span></p>
        <p><strong>Success rate:</strong> {report.success_rate:.1%}</p>
    </div>

    {self._format_changes_table(report)}
    {self._format_failed_files_table(failed_files)}
</body>
</html>
"""
        return html

    def _format_changes_table(self, report: MigrationReport) -> str:
        """Format changes summary table."""
        changes = report.summary.get("changes", {})
        if not changes:
            return ""

        rows = "\n".join(
            f"<tr><td>{change_type}</td><td>{count}</td></tr>"
            for change_type, count in changes.items()
        )

        return f"""
    <h2>Changes Applied</h2>
    <table>
        <tr><th>Change Type</th><th>Count</th></tr>
        {rows}
    </table>
"""

    def _format_failed_files_table(self, failed_files) -> str:
        """Format failed files table."""
        if not failed_files:
            return ""

        rows = "\n".join(
            f"""<tr>
                <td>{f.file_path.name}</td>
                <td>{f.processing_time:.2f}s</td>
                <td class="failed">{'<br>'.join(f.errors)}</td>
            </tr>"""
            for f in failed_files[:20]
        )

        return f"""
    <h2>Failed Files ({len(failed_files)})</h2>
    <table>
        <tr><th>File</th><th>Processing Time</th><th>Errors</th></tr>
        {rows}
    </table>
"""

    def save(self, report: MigrationReport, output_path: Path):
        """Save HTML report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(self.format(report))


class JSONFormatter:
    """JSON report formatter."""

    def format(self, report: MigrationReport) -> str:
        """Format report as JSON."""
        data = {
            "migration_id": report.migration_id,
            "profile": report.profile,
            "started_at": report.started_at.isoformat(),
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            "duration": report.duration,
            "total_files": report.total_files,
            "successful": report.successful,
            "failed": report.failed,
            "pending": report.pending,
            "success_rate": report.success_rate,
            "file_results": [
                {
                    "file_path": str(f.file_path),
                    "status": f.status,
                    "processing_time": f.processing_time,
                    "changes": f.changes,
                    "errors": f.errors,
                    "warnings": f.warnings,
                }
                for f in report.file_results
            ],
            "summary": report.summary,
        }
        return json.dumps(data, indent=2)

    def save(self, report: MigrationReport, output_path: Path):
        """Save JSON report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(self.format(report))
