{
    'name': 'Edge Autonomy Huntsville Odoo Modifications',
    'version': '1.0',
    'summary': 'A custom module for specific needs',
    'license': 'LGPL-3',
    'sequence': 1,
    'description': 'Currently just some CSS modifications to the frontend. More to come!',
    'category': 'Customizations',
    'website': 'https://www.edgeautonomy.io',
    'depends': ['base','stock','account', 'mrp', 'mrp_account', 'mrp_account_enterprise', 'mrp_mps', 'product', 'purchase', 'purchase_requisition', 'purchase_stock', 'quality_control', 'quality_mrp_workorder', 'sale', 'stock', 'stock_account', 'stock_barcode', 'stock_barcode_mrp'],
    'assets': {
        'web.assets_backend': [
            'edge_module/static/src/css/custom_styles.css'
        ],
    },
    'data': [
        # 'security/ir.model.access.csv,
        'views/views.xml',
        'views/StockMoveLine.xml',
        'views/custom_report_generic_barcode.xml',
         'data/custom_paper_format.xml',
    ],
    'demo': [
        # Demo data files
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}