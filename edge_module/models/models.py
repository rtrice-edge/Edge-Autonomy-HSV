#odoo procurement category

from odoo import models, fields


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
    ], string='Moisture Level (MSL)', required=True)

    fai = fields.Boolean(string='First Article Inspection (FAI)')

    qc = fields.Boolean(string='Receiving QC Required')


class StockMove(models.Model):
    _inherit = 'stock.move'

    noninventorymanufacturer = fields.Char(string='Non-Inventory Manufacturer')