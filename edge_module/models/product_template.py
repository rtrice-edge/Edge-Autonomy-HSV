#odoo procurement category
# All things related to the product Model should go here.  This includes the product template, product category, and product attribute models.  This is where you can add fields to the product template, or create new models to extend the product
from odoo import models, fields, api



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
    
    default_location_id = fields.Many2one(
        'stock.location',
        string='Default Location',
        domain=[('usage', '=', 'internal')]
    )
    
    
    @api.model
    def _get_default_location_selection(self):
        locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        return [(location.id, location.display_name) for location in locations]