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
                'security/security.xml',
        'security/ir.model.access.csv',

        'views/demand/component_mo_view.xml',
        'views/accountmapping/account_mapping_views.xml',
        'views/purchase/purchase_views.xml',
        
        'views/mrp/mrp_bom_view.xml',
        'views/mrp/mrp_production_work_order_form_inherit.xml',
        'views/mrp/mrp_production_workorder_search_view_inherit.xml',
        #'views/mrp/mrp_production_workorder_tree_view_inherit.xml',
         'views/mrp/mrp_production_view_kanban.xml',
         'views/mrp/mrp_production_views.xml',
         
        'views/product/product_fields.xml',
        'views/product/product_product_normal_form_view_inherit.xml',
        'views/product/product_template_form_inherit.xml',
        
        'views/project/project_form_inherit.xml',
        
        #'views/purchase_order/po_report.xml',asdfasdf
        'views/purchase_order/purchase_order_form_inherit.xml',
        'views/purchase_order/purchase_order_kpis_tree_inherit_urgency.xml',
        'views/purchase_order/purchase_order_search_inherit.xml',
        
        'views/quality/quality_check_view_tree_inherit.xml',
        'views/quality/quality_check_view_form_inherit.xml',
        'views/quality/quality_alert_team_dashboard_view_kanban.xml',
        
        'views/sale_order/sale_order_form.xml',
        
        #'views/stock/stock_move_line.xml',
        'views/stock/stock_picking_form.xml',
        'views/stock/stock_quant_print_lots.xml',
        'views/stock/stock_report_generic_barcode.xml',
        'views/stock/stock_picking_list.xml',
        'views/stock/stock_view_production_lot_form.xml',
        
        'views/trade_show_equipment/trade_show_equipment_views.xml',
        'views/trade_show_equipment/trade_show_views.xml',
        'views/trade_show_equipment/trade_show_shipment_views.xml',
        'views/trade_show_equipment/trade_show_locations_and_forwarders.xml',
        # 'views/trade_show_equipment/trade_show_equipment_home_location_views.xml',    
        
        'views/demand/demand_forceast.xml',
    
        'views/theme/theme.xml',
        'views/menu/menu.xml',

        'views/vendor/res_partner.xml',
        'views/helpdesk/helpdesk_ticket.xml',
        'reports/purchase_order_custom.xml',
        'reports/mo_pick_list_report.xml',
        'reports/report_mrp_order_detailed.xml',
        #'reports/traveler_report.qml',
        #'reports/ir_actions_report.xml',

        # 'reports/manufacturing_order_report.xml',

        'views/purchase_order/purchase_order.xml', 
        #'views/accountmove/view_move_form.xml',

        # 'views/mrp/manufacturing_report.xml',

        # 'views/mrp/manufacturing_report.xml',

        #'reports/mrp_report_mrporder.xml',

        #'reports/company_details_report.xml',

        'reports/report_delivery_document_custom.xml',
        'reports/report_purchaseorder_document.xml',
        'reports/purchase_open_lines_report_views.xml',
        'reports/request_for_quotation.xml'
        
    ],
    'demo': [
        # Demo data files
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}