odoo.define('your_module_name.custom_form_view', function (require) {
    'use strict';

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        _renderTagSelect: function (node) {
            var $select = this._super.apply(this, arguments);

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
        },
    });
});