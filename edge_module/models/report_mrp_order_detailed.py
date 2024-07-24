from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ReportMrpOrderDetailed(models.AbstractModel):
    _name = 'report.edge_module.report_mrp_order_detailed'
    _description = 'Detailed MO Report'

    def _get_initials(self, name):
        return ''.join([word[0].upper() for word in name.split() if word])

    def _get_worker_times(self, production):
        worker_times = {}
        for workorder in production.workorder_ids:
            worker_times[workorder.id] = {}
            for time_log in workorder.time_ids:
                worker = time_log.user_id
                if worker not in worker_times[workorder.id]:
                    worker_times[workorder.id][worker] = {'initials': self._get_initials(worker.name), 'time': 0}
                worker_times[workorder.id][worker]['time'] += time_log.duration
        return worker_times

    def _get_workorder_data(self, production):
        workorder_data = []
        worker_times = self._get_worker_times(production)
        for workorder in production.workorder_ids:
            comments = [
                {'initials': self._get_initials(message.author_id.name), 'body': message.body}
                for message in workorder.message_ids.filtered(lambda m: m.message_type == 'comment')
            ]
            workorder_data.append({
                'id': workorder.id,
                'name': workorder.name,
                'workcenter': workorder.workcenter_id.name,
                'duration': workorder.duration,
                'comments': comments,
                'date_finished': workorder.date_finished,
                'worker_times': worker_times.get(workorder.id, {})
            })
        return workorder_data

    def _prepare_production_data(self, production):
        try:
            return {
                'id': production.id,
                'name': production.name,
                'state': production.state,
                'product_id': production.product_id,
                'product_tmpl_id': production.product_id.product_tmpl_id if production.product_id else None,
                'lot_producing_id': production.lot_producing_id,
                'user_id': production.user_id,
                'product_qty': production.product_qty,
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
            }
            #commented out for now
        except Exception as e:
            _logger.error(f"Error preparing production data for MO {production.name}: {str(e)}")
            return {'name': production.name, 'error': str(e)}

    def _get_quality_checks(self, production):
        quality_checks = self.env['quality.check'].search([('production_id', '=', production.id)])
        check_data = []
        for check in quality_checks:
            check_data.append({
                'name': check.name,
                'point_id': check.point_id.name,
                'product_id': check.product_id.name,
                'lot_name': check.lot_name,
                'user_id': check.user_id.name,
                'date': check.control_date,
                'quality_state': check.quality_state,
                'measure': check.measure,
                'measure_success': check.measure_success,
                'comments': self._get_quality_check_comments(check),
            })
        return check_data

    def _get_quality_check_comments(self, check):
        return [
            {
                'author': self._get_initials(message.author_id.name),
                'date': message.date,
                'body': message.body
            }
            for message in check.message_ids.filtered(lambda m: m.message_type == 'comment')
        ]

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
                    'quality_checks': self._get_quality_checks(doc),
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