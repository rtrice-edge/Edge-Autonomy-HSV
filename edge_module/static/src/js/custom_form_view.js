/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";

export class CustomUrgencyRenderer extends SelectionField {
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

CustomUrgencyRenderer.template = "web.SelectionField";
CustomUrgencyRenderer.components = {
    FieldInput: CustomUrgencyRenderer,
};

registry.category("fields").add("custom_urgency_renderer", CustomUrgencyRenderer);