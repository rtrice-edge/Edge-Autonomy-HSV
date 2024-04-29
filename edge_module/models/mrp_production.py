from odoo import api, fields, models, _, Command

import logging
_logger = logging.getLogger(__name__)



class MrpProduction(models.Model):
    _inherit = 'mrp.production'

