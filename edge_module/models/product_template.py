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

    nsn = fields.Char(string='NSN')
    
    default_location_id = fields.Many2one('stock.location', compute='_compute_default_putaway_location', store=False)

    country_of_origin = fields.Many2one(
        'res.country', 
        string='Country of Origin', 
        default=lambda self: self.env['res.country'].search([('code', '=', 'US')], limit=1)
    )

    iuid_required = fields.Boolean(string='IUID Required')
    
    eccn = fields.Selection([
        ('', 'Not Specified'),
        ('EAR99', 'EAR99'),
        ('1A001', '1A001'),
        ('1A002', '1A002'),
        # Add more ECCN codes as needed
    ], string='ECCN', default='')

    ncnr = fields.Selection([
        ('', 'Not Specified'),
        ('cancellable_returnable', 'Cancellable and Returnable'),
        ('non_cancellable', 'Non-Cancellable'),
        ('non_returnable', 'Non-Returnable'),
        ('ncnr', 'Non-Cancellable and Non-Returnable')
    ], string='NCNR', default='')
    
    product_inventory_category = fields.Selection([
        ('A', 'Category A'),
        ('B', 'Category B'),
        ('C', 'Category C')
    ], string='Inventory Category', compute='_compute_inventory_category', store=True)

    product_owner = fields.Selection([
        ('slo', 'SLO'),
        ('aa', 'AA'),
        ('hsv', 'HSV'),
    ], string='Product Owner')


    @api.depends('standard_price')
    def _compute_inventory_category(self):
        for product in self:
            if not product.product_inventory_category:
                price = product.standard_price
                if price >= 100:
                    product.product_inventory_category = 'A'
                elif 10 <= price < 100:
                    product.product_inventory_category = 'B'
                else:
                    product.product_inventory_category = 'C'


    @api.depends('product_variant_ids')
    def _compute_default_putaway_location(self):
        for template in self:
            default_location = False
            for variant in template.product_variant_ids:
                default_location = self.env['stock.putaway.rule'].search(
                    [('product_id', '=', variant.id)], limit=1
                ).location_out_id
                if default_location:
                    break
            template.default_location_id = default_location

    
    
    @api.model
    def _get_default_location_selection(self):
        locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        return [(location.id, location.display_name) for location in locations]
    
    
    
def compute_product_inventory_category(env):
    products = env['product.template'].search([('product_inventory_category', 'in', [False, ''])])
    products._compute_inventory_category()