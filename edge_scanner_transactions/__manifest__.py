# -*- coding: utf-8 -*-
{
    'name': 'Edge Handheld Scanner',
    'version': '17.0.1.0.0',
    'summary': 'Scanner interface for inventory transfers',
    'category': 'Operations/Inventory',
    'sequence': 10,
    'author': 'Richard Trice',
    'website': 'https://www.edgeautonomy.io',
    'description': """
        This module provides a scanner interface for inventory transfers. It allows users to scan barcodes and perform inventory operations directly from the handheld scanner.
    """,
    'license': 'LGPL-3',
    'depends': ['base', 'stock'],
    'data': [
        'views/scanner_menu.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
