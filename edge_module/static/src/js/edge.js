/** @odoo-module **/

import { Component, onMounted } from '@odoo/owl';

export class QualityCheckButtonModifier extends Component {
    onMounted() {
        // Check if the environment has an action with the matching xml_id
        if (this.env.action && this.env.action.xml_id === "quality.check.view.form") {
            this._modifyButtons();
        }
    }

    _modifyButtons() {
        // Your custom logic to change the button labels or visibility
        const testTypeElement = this.el.querySelector("[name='test_type_id']");
        if (testTypeElement) {
            const testTypeText = testTypeElement.textContent.trim();
            if (testTypeText !== "Worksheet" && testTypeText !== "Pass - Fail") {
                const passButton = this.el.querySelector("button[name='do_pass']");
                const failButton = this.el.querySelector("button[name='do_fail']");
                const failDataButton = this.el.querySelector("button[data-value='fail']");
                const passDataButton = this.el.querySelector("button[data-value='pass']");
                if (passButton) passButton.textContent = "Complete";
                if (failButton) failButton.style.display = "none";
                if (failDataButton) failDataButton.style.display = "none";
                if (passDataButton) passDataButton.textContent = "Complete";
            }
        }
    }
}
