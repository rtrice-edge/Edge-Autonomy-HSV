from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class IrActionsReportTraveler(models.Model):
    _name = 'ir.actions.report.traveler'  # Custom name for your report action
    _inherit = 'ir.actions.report.custom'  # Inherit from your custom base class