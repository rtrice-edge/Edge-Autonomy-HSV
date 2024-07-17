from odoo import models, fields, api

class ReportMrpOrderDetailed(models.AbstractModel):
    _name = 'report.your_module.report_mrp_order_detailed'
    _description = 'Detailed MO Report'

    def _get_initials(self, name):
        return ''.join([word[0].upper() for word in name.split() if word])

    def _get_worker_times(self, production):
        worker_times = {}
        for workorder in production.workorder_ids:
            for time_log in workorder.time_ids:
                worker = time_log.user_id
                if worker not in worker_times:
                    worker_times[worker] = {'initials': self._get_initials(worker.name), 'time': 0}
                worker_times[worker]['time'] += time_log.duration
        return worker_times

    def _get_workorder_data(self, production):
        workorder_data = []
        for workorder in production.workorder_ids:
            comments = [
                {'initials': self._get_initials(message.author_id.name), 'body': message.body}
                for message in workorder.message_ids.filtered(lambda m: m.message_type == 'comment')
            ]
            workorder_data.append({
                'name': workorder.name,
                'workcenter': workorder.workcenter_id.name,
                'duration': workorder.duration,
                'comments': comments,
            })
        return workorder_data

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['mrp.production'].browse(docids)
        processed_docs = []
        for doc in docs:
            processed_docs.append({
                'id': doc.id,
                'name': doc.name,
                'product_id': doc.product_id,
                'lot_producing_id': doc.lot_producing_id,
                'lot_producing_ids': doc.lot_producing_ids,
                'user_id': doc.user_id,
                'product_qty': doc.product_qty,
                'product_uom_id': doc.product_uom_id,
                'date_start': doc.date_start,
                'date_finished': doc.date_finished,
                'bom_id': doc.bom_id,
                'worker_times': self._get_worker_times(doc),
                'workorder_data': self._get_workorder_data(doc),
                'move_raw_ids': doc.move_raw_ids,
            })
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': processed_docs,
        }