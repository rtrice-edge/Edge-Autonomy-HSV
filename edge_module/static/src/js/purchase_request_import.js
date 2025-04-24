odoo.define('edge_module.purchase_request_import', function (require) {
    "use strict";

    const ListController = require('web.ListController');
    const ListView = require('web.ListView');
    const viewRegistry = require('web.view_registry');

    const PurchaseRequestImportController = ListController.extend({
        /**
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments);
            
            if (this.$buttons) {
                // Add a new button right after "Create" button
                const $importButton = $('<button>', {
                    text: 'Import from Excel',
                    class: 'btn btn-secondary o_list_button_import_excel',
                    click: this._onImportExcel.bind(this),
                });
                
                // Insert after the create button
                this.$buttons.find('.o_list_button_add').after($importButton);
            }
        },

        /**
         * Handle click on import button
         *
         * @private
         */
        _onImportExcel: function () {
            this._rpc({
                model: 'purchase.request',
                method: 'action_open_import_wizard',
                args: [],
            }).then(action => {
                this.do_action(action);
            });
        },
    });

    const PurchaseRequestImportListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: PurchaseRequestImportController,
        }),
    });

    viewRegistry.add('purchase_request_import_tree', PurchaseRequestImportListView);

    return PurchaseRequestImportController;
});