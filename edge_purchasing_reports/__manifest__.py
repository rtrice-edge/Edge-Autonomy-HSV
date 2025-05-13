

{
    "name": "edge_purchasing_reports",
    "summary": "Edge Module for Purchasing Reporting",
    "version": "17.0",
    "category": "Purchase",
    "author": "Joseph Macfarlane",
    "website": "https://www.edgeautonomy.io",
    "description": """
        This module provides a custom report for purchase orders, focusing on on time delivery. It will include other reports in the future.
    """,
    "license": "AGPL-3",
    'depends': ['purchase', 'stock', 'edge_module'],

    'data': [
        'security/ir.model.access.csv',
        'views/on_time_delivery/on_time_delivery_views.xml',
        'views/on_time_delivery/on_time_delivery_view_selector_views.xml',
        'views/historical_po_lines/historical_po_wizard_view.xml',
        'views/historical_po_lines/purchase_order_line_search_extend.xml',
        'reports/purchase_lines_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}
