from odoo import models, api, fields
import logging
import math


_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_number = fields.Char(string='Tracking Number')
    carrier = fields.Char(string='Carrier')
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    delivery_price = fields.Monetary('Delivery Cost', currency_field='currency_id', default=0.0)
    alias = fields.Html(string='Alias', compute='_compute_alias', store=False)
    clickable_url = fields.Char(string='Clickable URL', compute='_compute_clickable_url')
    mo_product_id = fields.Many2one('product.product', string='MO Product', compute='_compute_mo_product_id')
    assigned_to = fields.Char(string='Assigned To', compute='_compute_assigned_to', store=False)
    mo_qty = fields.Float(string='MO Quantity', compute='_compute_mo_qty', store=False)
    mo_count = fields.Integer(string='Manufacturing Order Count', compute='_compute_mo_count')
    delivery_edge_recipient_new = fields.Many2one('hr.employee',compute='_compute_delivery_edge_recipient', string='Internal Recipient')
    dest_address_id = fields.Many2one('res.partner', string='Destination Address', compute='_compute_dest_address_id', store=True)

    helpdesk_count = fields.Integer(compute='_compute_helpdesk_count', string='Helpdesk Tickets')

    def _compute_helpdesk_count(self):
        for picking in self:
            picking.helpdesk_count = self.env['helpdesk.ticket'].search_count([
                ('stock_picking_id', '=', picking.id)
            ])

    def action_create_helpdesk_ticket(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Ticket',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'form',
            'context': {
                'default_stock_picking_id': self.id,
                'default_purchase_order_id': self.purchase_id.id,
            },
            'target': 'new',
        }

    def action_view_tickets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Helpdesk Tickets',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('stock_picking_id', '=', self.id)],
            'context': {'create': False},
        }







    @api.model
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            if picking.picking_type_code == 'incoming' and picking.origin:
                self._update_procurement_group(picking)
        return pickings

    def write(self, vals):
        result = super().write(vals)
        if 'origin' in vals:
            for picking in self:
                if picking.picking_type_code == 'incoming':
                    self._update_procurement_group(picking)
        return result

    def _update_procurement_group(self, picking):
        if picking.origin:
            ProcurementGroup = self.env['procurement.group']
            group = ProcurementGroup.search([('name', '=', picking.origin)], limit=1)
            if not group:
                group = ProcurementGroup.create({'name': picking.origin})
            
            picking.group_id = group.id

            # Update move lines
            picking.move_ids.write({'group_id': group.id})



    @api.depends('purchase_id')
    def _compute_dest_address_id(self):
        for picking in self:
            if picking.purchase_id:
                picking.dest_address_id = picking.purchase_id.dest_address_id
            else:
                picking.dest_address_id = False

    def _compute_delivery_edge_recipient(self):
        for picking in self:
            purchase_order = self.env['purchase.order'].search([('picking_ids', 'in', picking.id)], limit=1)
            if purchase_order:
                picking.delivery_edge_recipient_new = purchase_order.edge_recipient_new
            else:
                picking.delivery_edge_recipient_new = False

    def _compute_mo_count(self):
        for picking in self:
            picking.mo_count = self.env['mrp.production'].search_count([('group_id', '=', picking.group_id.id)])
    
    @api.depends('origin')
    def _compute_mo_qty(self):
        for picking in self:
                    if picking.origin:
                        production = self.env['mrp.production'].search([('name', '=', picking.origin)], limit=1)
                        if production:
                            picking.mo_qty = production.product_qty
                        else:
                            picking.mo_qty = False
                    else:
                        picking.mo_qty = False

    @api.depends('origin')
    def _compute_alias(self):
        for picking in self:
            if picking.origin:
                production = self.env['mrp.production'].search([('procurement_group_id', '=', picking.group_id.id)], limit=1)
                mo_count = self.env['mrp.production'].search_count([('procurement_group_id', '=', picking.group_id.id)])
                if production:
                    _logger.info(f"Production: {production}")
                    mo_number = production.name.split('/')[-1]  # Extract the numeric portion of the MO
                    product_code = production.product_id.default_code or ''
                    picking.alias = f"MO#{mo_number} Prd:{product_code}<br>Kits:{mo_count}&nbsp;&nbsp;&nbsp;KitQty:{production.product_qty}"
                    _logger.info(f"Alias: {picking.alias}")
                else:
                    picking.alias = ""
            else:
                picking.alias = ""

    @api.depends('origin')
    def _compute_assigned_to(self):
        for picking in self:
            if picking.origin:
                production = self.env['mrp.production'].search([('name', '=', picking.origin)], limit=1)
                if production and production.user_id:
                    picking.assigned_to = production.user_id.partner_id.name
                else:
                    picking.assigned_to = False
            else:
                picking.assigned_to = False

    @api.depends('origin')
    def _compute_mo_product_id(self):
        for picking in self:
            if 'MO' in picking.origin:
                mo_number = picking.origin.split('MO')[1].strip()
                mo = self.env['mrp.production'].search([('name', '=', mo_number)], limit=1)
                if mo:
                    picking.mo_product_id = mo.product_id
                else:
                    picking.mo_product_id = False
            else:
                picking.mo_product_id = False
    

    @api.depends('name')
    def _compute_clickable_url(self):
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record.clickable_url = f'{base_url}/web#id={record.id}&cids=1&menu_id=202&action=372&&model=stock.picking&view_type=form'
    
    def button_validate(self):
        # Check if this is a receipt
        if self.picking_type_code == 'incoming':
            # Temporarily disable the read access check for purchase.order
            self = self.with_context(bypass_purchase_order_check=True)
        
        return super(StockPicking, self).button_validate()

    @api.model
    def _read_group_check_purchase_order(self, orderby=None, groupby=None, domain=None, read_access_check=True):
        # Bypass purchase order check if the context flag is set
        if self.env.context.get('bypass_purchase_order_check'):
            read_access_check = False
        return super(StockPicking, self)._read_group_check_purchase_order(orderby=orderby, groupby=groupby, domain=domain, read_access_check=read_access_check)
    
    # def button_validate(self):
    #     res = super().button_validate()

    #     for picking in self:
    #         if picking.state == 'done':
    #             for move in picking.move_ids_without_package:
    #                 if move.production_id:
    #                     manufacturing_order = move.production_id
    #                     for move_line in move.move_line_ids:
    #                         if move_line.quantity > 0:
    #                             move_raw_id = manufacturing_order.move_raw_ids.filtered(lambda m: m.product_id == move.product_id)
    #                             if move_raw_id:
    #                                 move_raw_id.production_id = move_line.production_id
    #                                 self.env.cr.commit()  # Commit the changes to the database
    #                                 _logger.info(f"Updated consumed quantity for product {move.product_id.name} in MO {manufacturing_order.name}")
    #                             else:
    #                                 _logger.warning(f"Corresponding move_raw_id not found for product {move.product_id.name} in MO {manufacturing_order.name}")

    #     return res