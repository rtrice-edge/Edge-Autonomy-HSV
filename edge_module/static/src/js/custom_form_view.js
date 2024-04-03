import { FormRenderer } from "@web/views/form/form_renderer";

export class CustomFormRenderer extends FormRenderer {
    setup() {
        super.setup();
    }

    _renderTagSelect(node) {
        var $select = this._super(node);

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