{
    'name': 'Edge Autonomy Huntsville Odoo Modifications',
    'version': '1.0',
    'summary': 'A custom module for specific needs',
    'license': 'LGPL-3',
    'sequence': 1,
    'description': 'Currently just some CSS modifications to the frontend. More to come!',
    'category': 'Custom',
    'website': 'https://www.edgeautonomy.io',
    'depends': ['web_enterprise'],
    'assets': {
        'web.assets_frontend': [
            'edge_module/static/src/css/custom_styles.css',
        ],
    },
    'data': [
        # XML/YAML files
    ],
    'demo': [
        # Demo data files
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}