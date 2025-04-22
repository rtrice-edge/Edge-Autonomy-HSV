/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const fieldRegistry = registry.category('fields');

fieldRegistry.getEntries().forEach(([name, widget]) => {
    const supportedTypes = widget.supportedTypes || [];
    const supportedOptions = widget.supportedOptions || [];
    //console.log(`widget: ${widget}`, supportedTypes, supportedOptions); // Optional: for debugging
    const wantsPatch = (
        supportedTypes.includes('many2one') &&
        ['no_create', 'no_create_edit', 'no_quick_create'].some(opt =>
            supportedOptions.some(o => typeof o === 'string' ? o === opt : o.name === opt)
        )
    );

    if (wantsPatch && typeof widget.extractProps === 'function') {
        const originalExtractProps = widget.extractProps;
        console.log(`Patching widget: ${name}`); // Optional: for debugging
        patch(widget, {
            // Give the patch a slightly more descriptive name
            name: `edge_autonomy_slo.patch_extractProps_conditional_nocreate.${name}`,
            extractProps(props, ...args) {
                // Call the original function first to get its processed props
                const processedProps = originalExtractProps.call(this, props, ...args);

                console.log(`Processed props:`, processedProps); // Optional: for debugging
                const isLotSerialOnMO =
                    props.record?.resModel === 'mrp.production' &&
                    props.name === 'lot_producing_id';

                
                if (!isLotSerialOnMO) {
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
                    // return the props as processed by the original function,
                    // effectively allowing creation options defined in the XML view or defaults.
                    return processedProps;
                }
                // --- Conditional Logic End ---
            },
        });

        // console.log(`✅ Conditional extractProps patched: ${name}`); // Optional: for debugging
    }
});