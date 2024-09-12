from odoo import models, fields, api

class QualityAlert(models.Model):
    _inherit = 'quality.alert'

    # Override the name_get method to change how the record name is displayed
    def name_get(self):
        result = []
        for record in self:
            name = f"NCR {record.name}"
            result.append((record.id, name))
        return result

    # Optional: If you want to change the name of the model itself
    # Uncomment the following lines:
    _description = 'Non-Conformance Report'
    _rec_name = 'name'