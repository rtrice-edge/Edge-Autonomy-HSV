#odoo procurement category

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    costobjective = fields.Selection([
        ('direct', 'Direct'),
        ('g&a', 'G&A'),
        ('engovh', 'Eng OVH'),
        ('manovh', 'Man OVH'),
        ('ir&d', 'IR&D'),
        ('b&p', 'B&P')
    ], string='Cost Objective', required=True)


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
    ], string='Expense Type', required=True)

    
    fai = fields.Boolean(string='First Article Inspection (FAI)')


    url = fields.Char(string='Link to Prodct')


    vendor_product_name = fields.Char('Vendor Product Number', compute='_compute_vendor_product_name')

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_vendor_product_name(self):
        for line in self:
            vendor_info = line.product_id.seller_ids.filtered(
                lambda seller: seller.partner_id == line.order_id.partner_id)
            if vendor_info:
                line.vendor_product_name = vendor_info[0].product_name
            else:
                line.vendor_product_name = ''



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
