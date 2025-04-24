odoo.define('edge_module.purchase_request_import_tree', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var PurchaseRequestImportController = ListController.extend({
        /**
         * Add custom button to control panel
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments);
            
            if (this.$buttons) {
                // Add a new button right after "Create" button
                var $importButton = $('<button>', {
                    text: 'Import from Excel',
                    class: 'btn btn-secondary o_list_button_import_excel',
                });
                
                // Insert after the create button
                $importButton.on('click', this._onImportExcel.bind(this));
                this.$buttons.find('.o_list_button_add').after($importButton);
            }
        },

        /**
         * Handle click on import button
         *
         * @private
         */
        _onImportExcel: function () {
            var self = this;
            // Call the server action to open the import wizard
            this._rpc({
                model: 'purchase.request',
                method: 'action_open_import_wizard',
                args: [],
            })
            .then(function (action) {
                self.do_action(action);
            });
        },
    });

    var PurchaseRequestImportListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: PurchaseRequestImportController,
        }),
    });

    viewRegistry.add('purchase_request_import_tree', PurchaseRequestImportListView);

    return PurchaseRequestImportController;
});