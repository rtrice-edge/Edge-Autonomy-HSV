/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const fieldRegistry = registry.category('fields');

// Keep track of which widgets have been patched to avoid double patching
const patchedWidgets = new Set();

fieldRegistry.getEntries().forEach(([name, widget]) => {
    // Skip if already patched
    if (patchedWidgets.has(name)) {
        return;
    }
    
    const supportedTypes = widget.supportedTypes || [];
    const supportedOptions = widget.supportedOptions || [];
    
    const wantsPatch = (
        supportedTypes.includes('many2one') &&
        ['no_create', 'no_create_edit', 'no_quick_create'].some(opt =>
            supportedOptions.some(o => typeof o === 'string' ? o === opt : o.name === opt)
        )
    );

    if (wantsPatch && typeof widget.extractProps === 'function') {
        const originalExtractProps = widget.extractProps;
        
        patch(widget, {
            name: `edge_autonomy_slo.patch_extractProps_conditional_nocreate.${name}`,
            extractProps(props, ...args) {
                // Call the original function first to get its processed props
                const processedProps = originalExtractProps.call(this, props, ...args);
                
                // Reduce logging in production to avoid performance impact
                if (odoo.debug) {
                    console.log(`Processing widget: ${name}`);
                }
                
                const isLotSerialOnMO =
                    props.record?.resModel === 'mrp.production' &&
                    props.name === 'lot_producing_id';
                
                if (!isLotSerialOnMO) {
                    const patchedOptions = {
                        ...(processedProps.options || {}),
                        no_create: true,
                        no_create_edit: true,
                        no_quick_create: true,
                    };
                    return { ...processedProps, options: patchedOptions };
                } else {
                    return processedProps;
                }
            },
        });
        
        // Mark this widget as patched
        patchedWidgets.add(name);
    }
});