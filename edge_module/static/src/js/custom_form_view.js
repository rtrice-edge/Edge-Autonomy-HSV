/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";

export class CustomFormRenderer extends FormRenderer {
    setup() {
        super.setup();
    }

    _renderTagSelect(node) {
        var $select = this._super(node);
        console.log("I'm inside the custom form renderer");
        if (node.attrs.name === 'urgency') {
            console.log("I'm inside the urgency select")
            $select.find('option').each(function () {
                console.log("I'm inside the urgency select option")
                var $option = $(this);
                var value = $option.val();

                $option.addClass('btn');

                switch (value) {
                    case 'low':
                        
                        $option.addClass('btn-primary');
                        break;
                    case 'medium':
                        console.log("I'm inside the medium urgency")
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