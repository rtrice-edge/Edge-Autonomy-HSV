

{
    "name": "Supplier On-Time Performance",
    "summary": "Edge Module for Purchasing Reporting",
    "version": "17.0",
    "category": "Purchase",
    "author": "Joseph Macfarlane",
    "website": "https://www.edgeautonomy.io",
    "description": """
        This module provides a custom report for purchase orders, focusing on on time delivery. It will include other reports in the future.
    """,
    "license": "AGPL-3",
    'depends': ['purchase', 'stock'],

    'data': [
        'security/ir.model.access.csv',
        'views/on_time_delivery_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}
