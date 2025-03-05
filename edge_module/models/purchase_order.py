from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
import logging
from odoo.osv import expression
import traceback

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    admin_closed = fields.Boolean(string="Administratively Closed", default=False, readonly=True)

    # @api.depends('state', 'order_line.qty_to_invoice', 'admin_closed')
    # def _get_invoiced(self):
    #     precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #     for order in self:
    #         # If administratively closed, force invoice_status to 'no' ("Nothing to Bill")
    #         if order.admin_closed:
    #             order.invoice_status = 'no'
    #         # Otherwise, follow the standard logic
    #         elif order.state not in ('purchase', 'done'):
    #             order.invoice_status = 'no'
    #         elif any(
    #             not float_is_zero(line.qty_to_invoice, precision_digits=precision)
    #             for line in order.order_line.filtered(lambda l: not l.display_type)
    #         ):
    #             order.invoice_status = 'to invoice'
    #         elif (
    #             all(
    #                 float_is_zero(line.qty_to_invoice, precision_digits=precision)
    #                 for line in order.order_line.filtered(lambda l: not l.display_type)
    #             ) and order.invoice_ids
    #         ):
    #             order.invoice_status = 'invoiced'
    #         else:
    #             order.invoice_status = 'no'

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

    sensitive = fields.Boolean(
        string='Sensitive', default=False,
        help="If checked, only the creator and followers can see this order."
    )

    dpas_rating = fields.Selection(
        [
            ('dx', 'DX'),
            ('do', 'DO'),
        ],
        string='DPAS Rating'
    )
    
    tax_status = fields.Selection([
        ('', ''),
        ('exempt', 'Tax Exempt'),
        ('taxable', 'Taxable')
    ], string='Tax Status', default='', copy=True)

    def _get_tax_exempt_note(self):
        if self.tax_status == 'exempt':
            return "Order is tax exempt.\nAlabama State Sales and Use Tax Certificate of Exemption, No. EXM-R012010152."
        return ""
    
    def open_closure_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Administrative Closure',
            'res_model': 'administrative.closure.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('edge_module.view_administrative_closure_wizard_form').id,
            'target': 'new',
            'context': {'active_id': self.id},
        }
    project_name = fields.Selection(selection='_get_project_names', string='Project', help="Select the project that this purchase should be charged to. Find and edit the list of projects in the projects tab.")

    shipping_method = fields.Char(string='Shipping Method', help="Please input the carrier or shipping method for this purchase.")
    
    po_vendor_terms = fields.Char(string='Vendor Terms', help="This field will be automatically populated with any existing terms for the vendor. If none exist, this will be empty. An example is NET30.")

    edge_recipient_new = fields.Many2one('hr.employee', string='Internal Recipient', help="This is where you select the person who the package is to be delivered to when it enters the facility. This defaults as the person who created the purchase request.")

    user_id = fields.Many2one(
        'res.users', string='Purchaser',
        index=True, tracking=True,
        default=False,  # This removes the default value
        domain=lambda self: [('groups_id', 'in', self.env.ref('purchase.group_purchase_manager').id)]
    )

    




    #purchase_contact = fields.Many2one('hr.employee', string='Edge Contact')
    revision = fields.Integer(string='Amendment Count',copy=False)
    state = fields.Selection(selection_add=[('amendment', 'Amendment')])
    amendment_name = fields.Char('Order Reference', copy=True, readonly=True)
    current_amendment_id = fields.Many2one('purchase.order', 'Current Amendment', readonly=True)
    old_amendment_ids = fields.One2many('purchase.order', 'current_amendment_id', 'Old Amendment', readonly=True,
                                        context={'active_test': False})


    def action_merge_orders(self):
        """Merge selected purchase orders into the first one"""
        if len(self) < 2:
            raise UserError(_('Please select at least two purchase orders to merge.'))

        # Check if all orders have the same partner
        if len(self.mapped('partner_id')) > 1:
            raise UserError(_('Selected purchase orders must be from the same vendor.'))

        # Check if all orders are in draft state
        if any(po.state not in ['draft', 'sent','purchase'] for po in self):
            raise UserError(_('Only draft or sent purchase orders can be merged.'))

        # Sort by creation date and take the first one as main
        orders = self.sorted('create_date')
        main_po = orders[0]
        orders_to_merge = orders[1:]

        for order in orders_to_merge:
            # Move all lines to the main PO
            for line in order.order_line:
                line.write({
                    'order_id': main_po.id
                })
            
            # Add note about merge
            order.message_post(
                body=_('This purchase order has been merged into %s') % main_po.name,
                subtype_id=self.env.ref('mail.mt_note').id
            )
            
            # Cancel the merged order
            order.button_cancel()

        main_po.message_post(
            body=_('Merged with purchase orders: %s') % ', '.join(orders_to_merge.mapped('name')),
            subtype_id=self.env.ref('mail.mt_note').id
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': main_po.id,
            'view_mode': 'form',
            'target': 'current',
        }

 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]
    

    def action_reset_to_rfq(self):
        _logger.info('Called action_reset_to_rfq')
    
        for order in self:
            _logger.info("Order State: %s" % order.state)
            _logger.info("Receipt Status: %s" % order.receipt_status)
            if order.state not in ['sent', 'purchase'] or order.receipt_status != 'pending':
                raise exceptions.UserError('You can only reset orders in "RFQ Sent" or "Purchase Order" state that have not been received.')
            
            order.write({
                'state': 'draft',
                'date_approve': False,
            })
            
            # Reset related fields if necessary
            order.order_line.write({'state': 'draft'})
            
        return True

    
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
        if res.name:
            res.amendment_name = res.name
        return res
    


    @api.model
    def _search(self, args, offset=0, limit=None, order=None, access_rights_uid=None):
        if not self.env.is_superuser() and not self.env.user.has_group('purchase.group_purchase_manager'):
            sensitive_domain = [
                '|', '|', '|',
                ('sensitive', '=', False),
                ('message_follower_ids.partner_id', '=', self.env.user.partner_id.id),
                ('create_uid', '=', self.env.user.id),
                ('user_id', '=', self.env.user.id)
            ]
            args = expression.AND([args or [], sensitive_domain])
        return super()._search(args, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)

###################################
#
# Follower Access Control
#
#################################
    # @api.model
    # def _search(self, args, offset=0, limit=None, order=None, access_rights_uid=None):
    #     _logger.info("_search called on purchase.order")
    #     _logger.info(f"Args: {args}")
    #     _logger.info(f"Offset: {offset}, Limit: {limit}, Order: {order}")
    #     _logger.info(f"Current user: {self.env.user.name} (ID: {self.env.user.id})")
    #     _logger.info(f"Is superuser: {self.env.is_superuser()}")
    #     _logger.info(f"Has purchase manager rights: {self.env.user.has_group('purchase.group_purchase_manager')}")
        
    #     # Log the stack trace
    #     stack = traceback.extract_stack()
    #     _logger.info("Call stack:")
    #     for filename, lineno, name, line in stack[:-1]:  # Exclude the last item which is this line
    #         _logger.info(f"  File {filename}, line {lineno}, in {name}")
    #         if line:
    #             _logger.info(f"    {line.strip()}")

    #     if not self.env.is_superuser() and not self.env.user.has_group('purchase.group_purchase_manager'):
    #         follower_domain = [
    #             '|', '|', 
    #             ('message_follower_ids.partner_id', '=', self.env.user.partner_id.id),
    #             ('create_uid', '=', self.env.user.id),
    #             ('user_id', '=', self.env.user.id)
    #         ]
    #         args = expression.AND([args or [], follower_domain])
    #         _logger.info(f"Modified args after applying follower_domain: {args}")
        
    #     result = super()._search(args, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)
    #     _logger.info(f"_search result count: {len(result) if isinstance(result, list) else 'N/A'}")
    #     return result

#######################################################################



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



    # @api.model
    # def create(self, vals):
    #     _logger.info('Called create Purchase Order')
    #     res = super(PurchaseOrder, self).create(vals)
    #     if res.name:
    #         res.amendment_name = res.name
    #     return res

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

class AdministrativeClosureWizard(models.TransientModel):
    _name = 'administrative.closure.wizard'
    _description = 'Administrative Closure Wizard'

    reason = fields.Text(string="Administrative Reason for Closure", required=True)

    def apply_closure(self):
        _logger.info("Administrative Closure Wizard invoked.")
    
        purchase_order_id = self.env.context.get('active_id')
        if not purchase_order_id:
            _logger.warning("No active purchase order found in context.")
            return {'type': 'ir.actions.act_window_close'}

        purchase_order = self.env['purchase.order'].browse(purchase_order_id)
        purchase_order.message_post(body=f"Administrative Closure Reason: {self.reason}")

        stock_pickings = purchase_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        for picking in stock_pickings:
            picking.action_cancel()

        # Set the flag that our compute method checks
        purchase_order.write({'admin_closed': True})

        _logger.info("Purchase Order %s successfully marked as administratively closed.", purchase_order.name)
        return {'type': 'ir.actions.act_window_close'}
