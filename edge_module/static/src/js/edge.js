/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted } from "@odoo/owl";

patch(FormController.prototype, "edge_module", {
    setup() {
        // Call the original setup
        this._super();

        // `onMounted` runs after the FormController is rendered
        onMounted(() => {
            console.log("FormController onMounted. Action props:", this.props.action);

            // Check if we're in the quality.check.view.form
            if (this.props.action?.xml_id === "quality.check.view.form") {
                console.log("We are in the Quality Check form. Let's modify the buttons!");

                // Your custom logic
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
});
