

{
    "name": "edge_quality_reports",
    "summary": "Edge Module for Quality Reporting",
    "version": "17.0",
    "category": "Quality",
    "author": "Joseph Macfarlane",
    "website": "https://www.edgeautonomy.io",
    "description": """
        This module provides a custom report for quality checks. It will include other reports in the future.
    """,
    "license": "AGPL-3",
    'depends': [
        'quality',
        'purchase',
        'stock',
        'quality_control',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/quality_acceptance_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
