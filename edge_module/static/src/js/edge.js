/** @odoo-module **/

// import { core } from 'web.core';

// const _t = core._t; // If you need translation (though not used in this example)

$(document).ready(function () { // We can still use jQuery's $(document).ready for DOM manipulation
    "use strict";

    // Select the element with name='test_type_id'
    const $testTypeElement = $("[name='test_type_id']");

    // Check if the element exists on the page
    if ($testTypeElement.length > 0) {
        console.log("Element with name='test_type_id' found on the page.");

        // Get the text content of the element
        const testTypeText = $testTypeElement.text().trim();

        // Check if the text is NOT 'Worksheet' and NOT 'Pass - Fail'
        if (testTypeText !== 'Worksheet' && testTypeText !== 'Pass - Fail') {
            console.log("Condition met: Text is not 'Worksheet' or 'Pass - Fail'. Text is:", testTypeText);

            // Modify the 'do_pass' button
            $("button[name='do_pass']").text('Complete');
            console.log("Button [name='do_pass'] text changed to 'Complete'");

            // Hide the 'do_fail' button
            $("button[name='do_fail']").hide();
            console.log("Button [name='do_fail'] hidden");

            // Hide the button with data-value='fail'
            $("button[data-value='fail']").hide();
            console.log("Button [data-value='fail'] hidden");

            // Modify the button with data-value='pass'
            $("button[data-value='pass']").text('Complete');
            console.log("Button [data-value='pass'] text changed to 'Complete'");

        } else {
            console.log("Condition NOT met: Text is either 'Worksheet' or 'Pass - Fail'. Text is:", testTypeText);
            // Optionally, you can add code here to handle the 'else' condition
        }

    } else {
        console.log("Element with name='test_type_id' NOT found on the page. Skipping button modifications.");
    }
});