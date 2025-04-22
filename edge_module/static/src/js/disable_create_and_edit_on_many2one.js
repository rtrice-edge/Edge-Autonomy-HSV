/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const fieldRegistry = registry.category('fields');

fieldRegistry.getEntries().forEach(([name, widget]) => {
    const supportedTypes = widget.supportedTypes || [];
    const supportedOptions = widget.supportedOptions || [];
    //console.log(`widget: ${widget}`, supportedTypes, supportedOptions); // Optional: for debugging

    // Check if the widget supports many2one and any of the relevant 'no_create*' options
    const supportsMany2one = supportedTypes.includes('many2one');
    const supportsNoCreateOptions = ['no_create', 'no_create_edit', 'no_quick_create'].some(opt =>
        supportedOptions.some(o => typeof o === 'string' ? o === opt : o.name === opt)
    );

    // Check if the widget actually has an extractProps method to patch
    const hasExtractProps = typeof widget.extractProps === 'function';

    // Only proceed if all conditions are met
    if (supportsMany2one && supportsNoCreateOptions && hasExtractProps) {
        console.log(`Patching widget: ${name}`); // Optional: for debugging

        patch(widget, {
            // Give the patch a slightly more descriptive name
            name: `edge_autonomy_slo.patch_extractProps_conditional_nocreate.${name}`,
            extractProps(...args) { // Use spread syntax to capture all arguments
                // Call the original function using this._super
                // this._super refers to the function being patched (the original extractProps)
                const processedProps = this._super(...args);

                // --- Conditional Logic Start ---
                // Extract the 'props' object, which is usually the first argument
                const props = args[0];

                // Check if it's the Lot/Serial field on a Manufacturing Order
                const isLotSerialOnMO =
                    props.record?.resModel === 'mrp.production' &&
                    props.name === 'lot_producing_id';

                if (!isLotSerialOnMO) {
                    // If it's NOT the specific Lot/Serial field, enforce no_create options
                    const patchedOptions = {
                        ...(processedProps.options || {}), // Start with options from the original call's result
                        no_create: true,
                        no_create_edit: true,
                        no_quick_create: true,
                    };
                    // Return the original props structure but with our modified options
                    return { ...processedProps, options: patchedOptions };
                } else {
                    // If it *is* the Lot/Serial field on the MO form,
                    // return the props as processed by the original function (via _super),
                    // effectively allowing creation options defined elsewhere.
                    return processedProps;
                }
                // --- Conditional Logic End ---
            },
        });

        console.log(`✅ Conditional extractProps patched: ${name}`); // Optional: for debugging
    }
});