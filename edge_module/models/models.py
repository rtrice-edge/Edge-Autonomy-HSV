#odoo procurement category

from odoo import models, fields, api

from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, frozendict, split_every
from pytz import timezone, UTC
from collections import defaultdict
from datetime import datetime, time
from dateutil import relativedelta
from psycopg2 import OperationalError


import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    costobjective = fields.Selection([
        ('direct', 'Direct'),
        ('g&a', 'G&A'),
        ('engovh', 'Eng OVH'),
        ('manovh', 'Man OVH'),
        ('ir&d', 'IR&D'),
        ('b&p', 'B&P')
    ], string='Cost Objective', required=True ,default='direct')


    expensetype = fields.Selection([
        ('engineeringmaterials ', 'Engineering Materials '),
        ('electronicsmaterials ', 'Electronics Materials '),
        ('inventory/procurementmaterials ', 'Inventory/Procurement Materials '),
        ('composites/assemblymaterials ', 'Composites/Assembly Materials '),
        ('groundsupportmaterials ', 'Ground Support Materials '),
        ('subklabor-engineering ', 'Subk Labor-Engineering '),
        ('subklabor-composites/assembly ', 'Subk Labor-Composites/Assembly '),
        ('packing,postage,andfreight ', 'Packing, Postage, and Freight '),
        ('smalltooling ', 'Small Tooling '),
        ('itservices ', 'IT Services '),
        ('ithardware/peripherals ', 'IT Hardware/Peripherals '),
        ('itsoftware ', 'IT Software '),
        ('professionalservices/consultants ', 'Professional Services/Consultants '),
        ('supplies ', 'Supplies '),
        ('janitorial ', 'Janitorial '),
        ('repairs&maintenance ', 'Repairs & Maintenance '),
        ('equipmentrental ', 'Equipment Rental '),
        ('flighttesting ', 'Flight Testing '),
        ('smalltestequipment ', 'Small Test Equipment '),
        ('wastedisposal ', 'Waste Disposal '),
        ('safety ', 'Safety '),
    ], string='Expense Type', required=True, default='inventory/procurementmaterials ')

    
    fai = fields.Boolean(string='First Article Inspection (FAI)')


    url = fields.Char(string='Link to Prodct')


    vendor_number = fields.Char('Vendor Number')

    @api.onchange('product_id')
    def _onchange_product(self):
        self._update_vendor_number()

    def _update_vendor_number(self):
        # This method is called when the product_id is changed and updates the vendor_number field on the purchase order line
        # there is no price update here
        _logger.info('Called _update_vendor_number')
        if self.product_id and self.order_id.partner_id:
            product = self.product_id
            partner_id = self.order_id.partner_id.id
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('partner_id', '=', partner_id)
            ], limit=1)
            if supplier_info:
                _logger.info('called _update_vendor_number if statement and was true')
                self.vendor_number = supplier_info.product_name
            else:
                _logger.info('called _update_vendor_number else statement')
                self.vendor_number = False

    @api.onchange('price_unit')
    def _onchange_vendor_number(self):
        # This method is called when the price_unit is changed.  It looks to see if there is already a vendor price list record
        # with the same product and vendor number.  If there is, it updates the price.  If there is not, it creates a new record.
        _logger.info('Called _onchange_vendor_number')
        if self.vendor_number and self.product_id and self.order_id.partner_id:
            product = self.product_id
            partner_id = self.order_id.partner_id.id
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('partner_id', '=', partner_id),
                ('product_name', '=', self.vendor_number)
            ], limit=1)
            if not supplier_info:
                _logger.info('called _onchange_vendor_number if statement and was not true')
                self.env['product.supplierinfo'].create({
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'partner_id': partner_id,
                    'product_name': self.vendor_number,
                    'price': self.price_unit
                })
            else :
                _logger.info('called _onchange_vendor_number else statement')
                supplier_info.write({
                    'price': self.price_unit
                })
# import logging

# _logger = logging.getLogger(__name__)
# class StockWarehouseOrderpoint(models.Model):
#     _inherit = 'stock.warehouse.orderpoint'

#     def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=None, raise_user_error=True):
#         _logger.info("I clicked Order or Order to Max button")
#         res = super(StockWarehouseOrderpoint, self)._procure_orderpoint_confirm(use_new_cursor=use_new_cursor, company_id=company_id, raise_user_error=raise_user_error)
#         self = self.with_company(company_id)

#         for orderpoints_batch_ids in split_every(1000, self.ids):
#             if use_new_cursor:
#                 cr = registry(self._cr.dbname).cursor()
#                 self = self.with_env(self.env(cr=cr))
#             try:
#                 orderpoints_batch = self.env['stock.warehouse.orderpoint'].browse(orderpoints_batch_ids)
#                 all_orderpoints_exceptions = []
#                 while orderpoints_batch:
#                     procurements = []
#                     for orderpoint in orderpoints_batch:
#                         origins = orderpoint.env.context.get('origins', {}).get(orderpoint.id, False)
#                         if origins:
#                             origin = '%s - %s' % (orderpoint.display_name, ','.join(origins))
#                         else:
#                             origin = orderpoint.name
#                         if float_compare(orderpoint.qty_to_order, 0.0, precision_rounding=orderpoint.product_uom.rounding) == 1:
#                             date = orderpoint._get_orderpoint_procurement_date()
#                             global_visibility_days = self.env['ir.config_parameter'].sudo().get_param('stock.visibility_days')
#                             if global_visibility_days:
#                                 date -= relativedelta.relativedelta(days=int(global_visibility_days))
#                             values = orderpoint._prepare_procurement_values(date=date)
#                             procurements.append(self.env['procurement.group'].Procurement(
#                                 orderpoint.product_id, orderpoint.qty_to_order, orderpoint.product_uom,
#                                 orderpoint.location_id, orderpoint.name, origin,
#                                 orderpoint.company_id, values))

#                     try:
#                         with self.env.cr.savepoint():
#                             self.env['procurement.group'].with_context(from_orderpoint=True).run(procurements, raise_user_error=raise_user_error)
#                     except ProcurementException as errors:
#                         orderpoints_exceptions = []
#                         for procurement, error_msg in errors.procurement_exceptions:
#                             orderpoints_exceptions += [(procurement.values.get('orderpoint_id'), error_msg)]
#                         all_orderpoints_exceptions += orderpoints_exceptions
#                         failed_orderpoints = self.env['stock.warehouse.orderpoint'].concat(*[o[0] for o in orderpoints_exceptions])
#                         if not failed_orderpoints:
#                             _logger.error('Unable to process orderpoints')
#                             break
#                         orderpoints_batch -= failed_orderpoints

#                     except OperationalError:
#                         if use_new_cursor:
#                             cr.rollback()
#                             continue
#                         else:
#                             raise
#                     else:
#                         orderpoints_batch._post_process_scheduler()
#                         break

#                 # Log an activity on product template for failed orderpoints.
#                 for orderpoint, error_msg in all_orderpoints_exceptions:
#                     existing_activity = self.env['mail.activity'].search([
#                         ('res_id', '=', orderpoint.product_id.product_tmpl_id.id),
#                         ('res_model_id', '=', self.env.ref('product.model_product_template').id),
#                         ('note', '=', error_msg)])
#                     if not existing_activity:
#                         orderpoint.product_id.product_tmpl_id.sudo().activity_schedule(
#                             'mail.mail_activity_data_warning',
#                             note=error_msg,
#                             user_id=orderpoint.product_id.responsible_id.id or SUPERUSER_ID,
#                         )

#             finally:
#                 if use_new_cursor:
#                     try:
#                         cr.commit()
#                     finally:
#                         cr.close()
#                     _logger.info("A batch of %d orderpoints is processed and committed", len(orderpoints_batch_ids))

#         return {}


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manufacturer = fields.Char(string='Manufacturer')

    manufacturernumber = fields.Char(string='Manufacturer Number')

    msl = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('2A', '2A'),
        ('3', '3'),
        ('4', '4')
    ], string='Moisture Level (MSL)')

    qc = fields.Boolean(string='Receiving QC Required')

    altmanufacturer = fields.Char(string='Alternative Manufacturer')

    altmanufacturernumber = fields.Char(string='Alternative Manufacturer Number')


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    noninventorymanufacturer = fields.Char(string='Non-Inventory Manufacturer')

    noninventorymanufacturernumber = fields.Char(string='Non-Inventory Manufacturer Number')


class StockMoveExtension(models.Model):
    _inherit = 'stock.move'
    receiptsmsl = fields.Selection(related='product_id.product_tmpl_id.msl', string='M.S.L', readonly=True, store=True)
    #maybe maybe maybe



class ProjectTable(models.Model):
    _name = 'project.table'
    _description = 'Project Table'

    name = fields.Char('Purchases')
    project_id = fields.Many2one('project.project', string='Project')
    # Add any other fields you need for your table


class Project(models.Model):
    _inherit = 'project.project'

    project_purchases = fields.One2many('project.table', 'project_id', string='Project Purchases')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
 
    project_name = fields.Selection(selection='_get_project_names', string='Project')
 
    @api.model
    def _get_project_names(self):
        projects = self.env['project.project'].search([('active', '=', True)])
        return [(project.name, project.name) for project in projects]
    

    @api.onchange('partner_id')
    def _onchange_partner(self):
        for line in self.order_line:
            line._update_vendor_number()