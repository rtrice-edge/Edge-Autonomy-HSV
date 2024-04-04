/** @odoo-module **/

import { FieldSelection } from "@web/views/fields/selection/selection_field";
import { registry } from "@web/core/registry";

export class CustomUrgencyRenderer extends FieldSelection {
    async _renderEdit(record, node) {
        const $select = await super._renderEdit(record, node);
        
        $select.find('option').each(function () {
            var $option = $(this);
            var value = $option.val();

            $option.addClass('btn');

            switch (value) {
                case 'low':
                    $option.addClass('btn-primary');
                    break;
                case 'medium':
                    $option.addClass('btn-warning');
                    break;
                case 'high':
                    $option.addClass('btn-danger');
                    break;
                case 'stoppage':
                    $option.addClass('btn-danger blinking');
                    break;
            }
        });

        return $select;
    }
}

registry.category("fields").add("custom_urgency_renderer", CustomUrgencyRenderer);