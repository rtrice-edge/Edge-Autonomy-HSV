from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    urgency = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('stoppage', 'Stoppage'),
        ],
        string='Urgency',
        default='low',
        help="Select the urgency level of this item. 'Stoppage' indicates a critical issue that halts operations."
    )
    project_name = fields.Selection(selection='_get_project_names', string='Project', help="Select the project that this purchase should be charged to. Find and edit the list of projects in the projects tab.")
    shipping_method = fields.Char(string='Shipping Method', help="Please input the carrier or shipping method for this purchase.")
    
    po_vendor_terms = fields.Char(string='Vendor Terms', help="This field will be automatically populated with any existing terms for the venor. If none exist, this will be empty. An example is NET30.")

    edge_recipient_new = fields.Many2one('hr.employee', string='Internal Recipient', help="This is where you select the person who the package is to be delivered to when it enters the facility. This defailts as the person who created the purchase request.")

    #purchase_contact = fields.Many2one('hr.employee', string='Edge Contact')
    revision = fields.Integer(string='Amendment Count',copy=False)
    state = fields.Selection(selection_add=[('amendment', 'Amendment')])
    amendment_name = fields.Char('Order Reference', copy=True, readonly=True)
    current_amendment_id = fields.Many2one('purchase.order', 'Current Amendment', readonly=True)
    old_amendment_ids = fields.One2many('purchase.order', 'current_amendment_id', 'Old Amendment', readonly=True,
                                        context={'active_test': False})

 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]


    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        _logger.info('Called onchange partner_id')
        if self.partner_id:
            self.po_vendor_terms = self.partner_id.vendor_terms
        if self.requisition_id:
            _logger.info('There was a requisition_id in the vals')
            requisition = self.env['purchase.requisition'].browse(self.requisition_id.id)
            _logger.info(requisition)
            if requisition:
                for i, line in enumerate(requisition.line_ids):
                    _logger.info(line.product_description_variants)
                    if i < len(self.order_line):
                        _logger.info("I'm in the loop!")
                        _logger.info(self.order_line[i].name)
                        self.order_line[i].name = line.product_description_variants
                        _logger.info(self.order_line[i].name)
        
        
    
    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        res.po_vendor_terms = res.partner_id.vendor_terms
        return res

    # @api.model_create_multi
    # def create(self, vals):
    #     _logger.info('Called create Purchase Order')
    #     _logger.info(vals)
    #     if vals.get('requisition_id'):
    #         _logger.info('There was a requisition_id in the vals')
    #         requisition = self.env['purchase.requisition'].browse(vals['requisition_id'])
    #         _logger.info(requisition)
    #         if requisition:
    #             for line in requisition.line_ids:
    #                 _logger.info(line)
    #                 for order_line in vals.get('order_line', []):
    #                     _logger.info(order_line)
    #                     order_line['name'] = line.product_description_variants
    #     return super(PurchaseOrder, self).create(vals)



    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        if res.name:
            res.amendment_name = res.name
        return res

    def button_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent', 'amendment'])
        orders.write({
            'state': 'draft',
        })

    def create_amendment(self):
        self.ensure_one()
        # Assign Form view before amendment
        view_ref = self.env['ir.model.data'].check_object_reference('purchase', 'purchase_order_form')
        view_id = view_ref and view_ref[1] or False,
        self.with_context(new_purchase_amendment=True).copy()
        self.write({'state': 'draft'})
        self.order_line.write({'state': 'draft'})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    @api.returns('self', lambda value: value.id)
    def copy(self, defaults=None):
        if not defaults:
            defaults = {}
        if self.env.context.get('new_purchase_amendment'):
            prev_name = self.name
            revno = self.revision
            amendment_ids = self.old_amendment_ids.ids
            # Assign default values for views
            self.write({'revision': revno + 1, 'name': '%s-%02d' % (self.amendment_name, revno + 1)})
            defaults.update({'name': prev_name, 'revision': revno, 'state': 'cancel', 'invoice_count': 0,
                             'current_amendment_id': self.id, 'amendment_name': self.amendment_name,
                             })
        return super(PurchaseOrder, self).copy(defaults)

    def button_amend(self):
        prev_name = self.name
        for purchase in self:
            for picking_loop in purchase.picking_ids:
                if picking_loop.state == 'done':
                    raise UserError(
                        f"Unable to amend purchase order {prev_name}, as some receptions have already been processed."
                    )
                else:
                    picking_loop.filtered(lambda r: r.state != 'cancel').action_cancel()
            for invoice_loop in purchase.invoice_ids:
                if invoice_loop.state != 'draft':
                    raise UserError(
                        'Unable to amend this purchase order, You must first cancel all Supplier Invoices related to '
                        'this purchase order.')
                else:
                    invoice_loop.filtered(lambda r: r.state != 'cancel').action_invoice_cancel()
        self.button_draft()
        self.create_amendment()
        self.write({'state': 'amendment'})