

{
    "name": "edge_demand_report",
    "summary": "Edge Module for Demand Reporting",
    "version": "17.0",
    "category": "Purchase",
    "author": "Joseph Macfarlane",
    "website": "https://www.edgeautonomy.io",
    "description": """
        This module provides a custom report for demand.
    """,
    "license": "AGPL-3",
    'depends': ['purchase', 'stock', 'edge_module'],

    'data': [
        'security/ir.model.access.csv',
        'views/demand_sortable.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}
