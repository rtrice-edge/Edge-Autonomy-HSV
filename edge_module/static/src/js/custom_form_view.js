odoo.define('edge_module.custom_form_view',[], function (require) {
    'use strict';

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.extend({
        _renderTagSelect: function (node) {
            // console.log("I made it into here, and we can see the node: ", node.attrs.name)
            var $select = this._super.apply(this, arguments);

            if (node.attrs.name === 'urgency') {
                // console.log("I found the urgency and its great!")
                $select.find('option').each(function () {
                    var $option = $(this);
                    var value = $option.val();
                    
                    $option.addClass('btn');
                    // console.log("I found the options!")
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
    return {Renderer: FormRenderer};
   
});