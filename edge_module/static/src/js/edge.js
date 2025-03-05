/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted } from "@odoo/owl";

const originalSetup = FormController.prototype.setup;

patch(FormController.prototype, {
    // Give your patch a unique name (third argument)
}, "edge_module_form_patch");

patch(FormController.prototype, {
    setup() {
        // Call the original setup
        originalSetup.call(this);

        // Add your custom logic
        onMounted(() => {
            console.log("FormController onMounted. Action props:", this.props.action);

            // Example: Only run for the 'quality.check.view.form'
            if (this.props.action?.xml_id === "quality.check.view.form") {
                console.log("We are in the Quality Check form. Let's modify the buttons!");
                // Perform your DOM manipulation or button changes here
                const testTypeElement = document.querySelector("[name='test_type_id']");
                if (testTypeElement) {
                    const testTypeText = testTypeElement.textContent.trim();
                    if (testTypeText !== "Worksheet" && testTypeText !== "Pass - Fail") {
                        const passButton = document.querySelector("button[name='do_pass']");
                        const failButton = document.querySelector("button[name='do_fail']");
                        const failDataButton = document.querySelector("button[data-value='fail']");
                        const passDataButton = document.querySelector("button[data-value='pass']");

                        if (passButton) passButton.textContent = "Complete";
                        if (failButton) failButton.style.display = "none";
                        if (failDataButton) failDataButton.style.display = "none";
                        if (passDataButton) passDataButton.textContent = "Complete";
                    }
                }
            }
        });
    },
}, "edge_module");
