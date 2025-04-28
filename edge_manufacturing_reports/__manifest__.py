

{
    "name": "edge_manufacturing_reports",
    "summary": "Edge Module for Manufacturing Reporting",
    "version": "17.0",
    "category": "Manufacturing",
    "author": "Richard Trice",
    "website": "https://www.edgeautonomy.io",
    "description": """
        This module provides a custom report for manufacturing orders, focusing on time and quality checks. It will include other reports in the future.
    """,
    "license": "AGPL-3",
    "depends": ["web",'hr', 'quality_mrp'],

    'data': [
        'security/security.xml',
        'views/mo_time_quality_report_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}
