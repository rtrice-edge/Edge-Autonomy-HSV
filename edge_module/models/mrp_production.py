from odoo import api, fields, models, _, Command

import logging
_logger = logging.getLogger(__name__)



class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_split(self):
        self._pre_action_split_merge_hook(split=True)
        _logger.info('Called action_split')
        _logger.info(self)
        _logger.info(self.values())
        if len(self.production) > 1:
            productions = []
            for production in self:
                # Create a new procurement group for each split MO
                procurement_group = self.env['procurement.group'].create({'name': production.name})
                _logger.info('Created procurement group' + str(procurement_group))
                # Assign the new procurement group to the split MO
                production_data = {'production_id': production.id, 'procurement_group_id': procurement_group.id}
                productions.append(Command.create(production_data))
            
            # Wizard needs a real ID to have buttons enabled in the view
            wizard = self.env['mrp.production.split.multi'].create({'production_ids': productions})
            action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
            action['res_id'] = wizard.id
            return action
        else:
            action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split')
            action['context'] = {
                'default_production_id': self.id,
            }
            return action