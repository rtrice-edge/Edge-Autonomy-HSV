from odoo import api, fields, models, _
from odoo.exceptions import UserError
import re
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class ReportMrpOrderDetailed(models.AbstractModel):
    _name = 'report.edge_module.report_mrp_order_detailed'
    _description = 'Detailed MO Report'
    
    def _get_quality_alerts(self, production):
        alerts = []
        try:
            _logger.debug(f"Fetching quality alerts for MO: {production.name} (ID: {production.id})")
            _logger.debug(f"Product ID: {production.product_id.id}, Lot ID: {production.lot_producing_id.id if production.lot_producing_id else 'None'}")
            
            domain = [
                ('product_id', '=', production.product_id.id),
                ('lot_id', '=', production.lot_producing_id.id),
            ]
            _logger.debug(f"Quality alert search domain: {domain}")
            
            quality_alerts = self.env['quality.alert'].search(domain)
            _logger.debug(f"Found {len(quality_alerts)} quality alerts")
            
            for alert in quality_alerts:
                alert_data = {
                    'name': alert.name,
                    'reason': alert.reason_id.name if alert.reason_id else None,
                    'description': alert.description,
                    'date_assign': alert.date_assign,
                    'workorder_name': alert.workorder_id.name if alert.workorder_id else 'N/A',
                    'user_id': alert.user_id.name if alert.user_id else None,
                    'status': alert.stage_id.name if alert.stage_id else None,
                }
                _logger.debug(f"Processing alert: {alert_data}")
                alerts.append(alert_data)
        except Exception as e:
            _logger.error(f"Error getting quality alerts for MO {production.name}: {str(e)}", exc_info=True)
        return alerts
    

    def _get_worker_times(self, workorder):
        worker_times = {}
        for time_log in workorder.time_ids:
            worker = time_log.user_id
            if worker not in worker_times:
                worker_times[worker] = {'name': worker.name, 'time': 0}
            worker_times[worker]['time'] += time_log.duration
        return worker_times

    def _get_consumable_lots(self, workorder):
        return [{
            'product_name': lot.product_id.name,
            'lot_id': lot.lot_id,
            'expiration_date': lot.expiration_date,
        } for lot in workorder.consumable_lot_ids]
    
    def _get_workorder_instructions(self, workorder):
        return workorder.operation_id.note if workorder.operation_id else None
    
    def _get_quality_check_instructions(self, workorder):
        if workorder.quality_check_id and workorder.quality_check_id.point_id:
            return workorder.quality_check_id.point_id.note
        return None

    def _get_quality_check_history(self, workorder):
        quality_check = workorder.quality_check_id
        if not quality_check:
            return []
        
        history = []
        try:
            for message in quality_check.message_ids:
                tracking_value = message.tracking_value_ids.filtered(lambda tv: tv.field_id.id == 8177)
                if tracking_value and tracking_value.new_value_char in ['Passed', 'Failed']:
                    history.append({
                        'date': message.date,
                        'status': tracking_value.new_value_char,
                        'user_name': message.author_id.name,
                        'comment': message.body,
                    })
        except Exception as e:
            _logger.error(f"Error processing quality check history for workorder {workorder.id}: {str(e)}")
        
        return sorted(history, key=lambda x: x['date'], reverse=True)
    
    
    def _get_workorder_comments(self, workorder):
        return [
            {
                'author': message.author_id.name,
                'date': message.date,
                'body': message.body
            }
            for message in workorder.message_ids.filtered(lambda m: m.message_type == 'comment')
        ]

    def _get_quality_alert_info(self, workorder):
        quality_check = workorder.quality_check_id
        if not quality_check:
            return None
        
        quality_alert = quality_check.alert_ids
        if not quality_alert:
            return None
        
        try:
            return {
                'name': quality_alert.name,
                'reason': quality_alert.reason_id.name if quality_alert.reason_id else None,
                'description': quality_alert.description,
                'date_assign': quality_alert.date_assign,
                'user_id': quality_alert.user_id.name if quality_alert.user_id else None,
                'status': quality_alert.stage_id.name if quality_alert.stage_id else None,
            }

        except Exception as e:
            _logger.error(f"Error processing quality alert for workorder {workorder.id}: {str(e)}")
            return None
    def _get_sub_mos(self, production, processed_mos=None):
        if processed_mos is None:
            processed_mos = set()

        sub_mos = []
        for move in production.move_raw_ids:
            if move.lot_ids:  # Check if the component has lot/serial numbers
                for lot in move.lot_ids:
                    # Find the MO that produced this lot
                    producing_mo = self.env['mrp.production'].search([
                        ('lot_producing_id', '=', lot.id),
                        ('product_id', '=', move.product_id.id)
                    ], limit=1)
                    
                    if producing_mo and producing_mo.id not in processed_mos:
                        # Check if the product's category is not 'manufactured wire'
                        if producing_mo.product_id.categ_id.name.lower() != 'manufactured wire':
                            processed_mos.add(producing_mo.id)
                            sub_mo_data = {
                                'mo_number': producing_mo.name,
                                'product_number': producing_mo.product_id.default_code or producing_mo.product_id.name,
                                'date_completed': producing_mo.date_finished,
                            }
                            sub_mos.append(sub_mo_data)
                            # Recursively get sub-MOs and extend the list
                            sub_mos.extend(self._get_sub_mos(producing_mo, processed_mos))

        return sub_mos

    
    
    def _get_workorder_data(self, production):
        def get_sequence_number(workorder):
            # Extract the first number from the name, consistent with _compute_sequence_number
            match = re.match(r'^(\d+)', workorder.name or '')
            return int(match.group(1)) if match else 999999

        workorder_data = []
        # Sort first by sequence number, then by date_finished as a secondary sort
        for workorder in production.workorder_ids.sorted(
            key=lambda w: (get_sequence_number(w), w.date_finished or datetime.max)
        ):
            quality_check_history = self._get_quality_check_history(workorder)
            quality_alert_info = self._get_quality_alert_info(workorder)
            workorder_data.append({
                'id': workorder.id,
                'name': workorder.name,
                'workcenter': workorder.workcenter_id.name,
                'duration': workorder.duration,
                'date_finished': workorder.date_finished,
                'worker_times': self._get_worker_times(workorder),
                'consumable_lots': self._get_consumable_lots(workorder),
                'quality_check': {
                    'history': quality_check_history,
                    'instructions': self._get_quality_check_instructions(workorder)
                } if quality_check_history else None,
                'quality_alert': quality_alert_info,
                'comments': self._get_workorder_comments(workorder),
                'instructions': self._get_workorder_instructions(workorder),  
            })
        return workorder_data

    def _get_mo_comments(self, production):
        return [
            {
                'author': message.author_id.name,
                'date': message.date,
                'body': message.body
            }
            for message in production.message_ids.filtered(lambda m: m.message_type == 'comment')
        ]

    def _prepare_production_data(self, production):
        try:
            data = {
                'id': production.id,
                'name': production.name,
                'state': production.state,
                'product_id': production.product_id,
                'product_tmpl_id': production.product_id.product_tmpl_id if production.product_id else None,
                'lot_producing_id': production.lot_producing_id,
                'user_id': production.user_id,
                'product_qty': production.product_qty,
                'qty_producing' : production.qty_producing,
                'product_uom_id': production.product_uom_id,
                'date_start': production.date_start,
                'date_finished': production.date_finished,
                'bom_id': production.bom_id,
                'move_raw_ids': production.move_raw_ids,
                'move_finished_ids': production.move_finished_ids,
                'workorder_ids': production.workorder_ids,
                'company_id': production.company_id,
                'production_location_id': production.production_location_id,
                'qty_producing': production.qty_producing,
                'product_uom_qty': production.product_uom_qty,
                'comments': self._get_mo_comments(production),
                'sub_mos': self._get_sub_mos(production),  # This now includes all levels of sub-MOs
                'quality_alerts': self._get_quality_alerts(production),  # Added quality alerts
            }
            return data
        except Exception as e:
            _logger.error(f"Error preparing production data for MO {production.name}: {str(e)}")
            return {'name': production.name, 'error': str(e)}


    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info(f"Generating report for docids: {docids}")
        docs = self.env['mrp.production'].browse(docids)
        processed_docs = []
        for doc in docs:
            _logger.info(f"Processing document: {doc.name}")
            try:
                production_data = self._prepare_production_data(doc)
                processed_doc = {
                    'production': production_data,
                    'workorder_data': self._get_workorder_data(doc),
                    'sub_mos': self._get_sub_mos(doc),
                    'o': doc,  # Pass the original record
                }
                processed_docs.append(processed_doc)
            except Exception as e:
                _logger.error(f"Error processing document {doc.name}: {str(e)}")
                processed_doc = {
                    'production': {'name': doc.name, 'error': str(e)},
                    'error': str(e),
                    'o': doc,  # Pass the original record even in case of error
                }
                processed_docs.append(processed_doc)

        _logger.info(f"Returning {len(processed_docs)} processed documents")
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': processed_docs,
        }