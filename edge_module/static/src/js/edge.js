/** @odoo-module **/

import { core } from '@web.core';


// Listen for the 'dom-ready' event on Odoo's bus
core.bus.on('dom-ready', null, function () { // Use core.bus.on
    "use strict";

    console.log("dom-ready event fired - Odoo DOM is likely ready.");

    // Now try to find the element and perform actions
    var $testTypeElement = $("[name='test_type_id']");

    if ($testTypeElement.length > 0) {
        console.log("Element with name='test_type_id' found on the page.");
        var testTypeText = $testTypeElement.text().trim();
        if (testTypeText !== 'Worksheet' && testTypeText !== 'Pass - Fail') {
            console.log("Condition met: Text is not 'Worksheet' or 'Pass - Fail'. Text is:", testTypeText);
            $("button[name='do_pass']").text('Complete');
            $("button[name='do_fail']").hide();
            $("button[data-value='fail']").hide();
            $("button[data-value='pass']").text('Complete');
        } else {
            console.log("Condition NOT met: Text is either 'Worksheet' or 'Pass - Fail'. Text is:", testTypeText);
        }
    } else {
        console.log("Element with name='test_type_id' NOT found on the page.");
    }
});