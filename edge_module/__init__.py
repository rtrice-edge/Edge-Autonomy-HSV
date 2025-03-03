from . import xlsx_reports
from . import models
from . import controllers
from odoo import SUPERUSER_ID, api
from .models.product_template import compute_product_inventory_category
from dateutil.relativedelta import relativedelta


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.ui.view'].clear_caches()
    
    compute_product_inventory_category(env)
    
    
    

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.ui.view'].clear_caches()