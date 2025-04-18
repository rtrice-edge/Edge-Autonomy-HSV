/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const fieldRegistry = registry.category('fields');

fieldRegistry.getEntries().forEach(([name, widget]) => {
    const supportedTypes = widget.supportedTypes || [];
    const supportedOptions = widget.supportedOptions || [];
    console.log(`widget: ${name}`, supportedTypes, supportedOptions);
    const wantsPatch = (
        supportedTypes.includes('many2one') &&
        ['no_create', 'no_create_edit', 'no_quick_create'].some(opt =>
            supportedOptions.some(o => typeof o === 'string' ? o === opt : o.name === opt)
        )
    );

    if (wantsPatch && typeof widget.extractProps === 'function') {
        const originalExtractProps = widget.extractProps;
        console.log(`Patching widget: ${name}`);
        patch(widget, {
            name: `edge_autonomy_slo.patch_extractProps.${name}`,
            extractProps(props, ...args) {
                const patchedOptions = {
                    ...(props.options || {}),
                    no_create: true,
                    no_create_edit: true,
                    no_quick_create: true,
                };
                const patchedProps = { ...props, options: patchedOptions };
                return originalExtractProps.call(this, patchedProps, ...args);
            },
        });

        console.log(`✅ extractProps patched: ${name}`);
    }
});
