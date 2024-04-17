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
            'edge_module/static/src/js/custom_form_view.js',
            'edge_module/static/src/css/custom_styles.css'
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        
       'views/mrp/mrp_bom_view.xml',
       
        'views/product/product_fields.xml',
        'views/product/product_product_normal_form_view_inherit.xml',
        'views/product/product_template_form_inherit.xml',
        
        'views/project/project_form_inherit.xml',
        
        #'views/purchase_order/po_report.xml',
        'views/purchase_order/purchase_order_form_inherit.xml',
        'views/purchase_order/purchase_order_kpis_tree_inherit_urgency.xml',
        'views/purchase_order/purchase_order_search_inherit.xml',
        
        'views/sale_order/sale_order_form.xml',
        
        'views/stock/stock_move_line.xml',
        'views/stock/stock_picking_form.xml',
        'views/stock/stock_quant_print_lots.xml',
        'views/stock/stock_report_generic_barcode.xml',
        
        'views/trade_show_equipment/trade_show_equipment_views.xml',
        'views/trade_show_equipment/trade_show_views.xml',
        'views/trade_show_equipment/trade_show_shipment_views.xml',
        'views/trade_show_equipment/trade_show_equipment_home_location_views.xml',    
        
        'views/purchase/projected_shortages_template.xml',
        'views/purchase/purchase_menu.xml',
    
        'views/theme/theme.xml',
        'views/menu/menu.xml',

        'views/vendor/res_partner.xml',
        
    ],
    'demo': [
        # Demo data files
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}