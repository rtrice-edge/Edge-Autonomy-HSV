from odoo import models

class ManufacturingOrder(models.Model):
    _inherit = 'mrp.production'

    def action_manufacturing_order_report(self):
        return self.env.ref('your_module.report_manufacturing_order').report_action(self)