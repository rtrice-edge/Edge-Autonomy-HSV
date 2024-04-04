/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";
import { registry } from "@web/core/registry";

export class CustomFormRenderer extends FormRenderer {
    async _renderTagSelect(node) {
        console.log('CustomFormRenderer._renderTagSelect', node);
        const $select = await super._renderTagSelect(node);

        if (node.attrs.name === 'urgency') {
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
        }

        return $select;
    }
}

registry.category("form_renderer").add("custom_form_renderer", CustomFormRenderer);