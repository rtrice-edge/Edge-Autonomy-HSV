import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "../standard_widget_props";
import { Component } from "@odoo/owl";

/**
 * This widget adds a large ribbon on the top right side of the form.
 * It is designed to be larger than the standard ribbon and offset so that both can be displayed simultaneously.
 *
 * You can specify the text with the text prop, the tooltip with the title prop, and
 * the background color with the bg_color prop (using bootstrap classes like text-bg-success, etc.).
 */
class BigRibbonWidget extends Component {
    static template = "web.BigRibbon"; // Create a new template (see note below)
    static props = {
        ...standardWidgetProps,
        text: { type: String },
        title: { type: String, optional: true },
        bgClass: { type: String, optional: true },
    };
    static defaultProps = {
        title: "",
        bgClass: "text-bg-success",
    };

    get classes() {
        // Add an extra class for custom styling (e.g., bigger size and offset)
        let classes = `${this.props.bgClass} big_ribbon`;
        if (this.props.text.length > 15) {
            classes += " o_small";
        } else if (this.props.text.length > 10) {
            classes += " o_medium";
        }
        return classes;
    }
}

export const bigRibbonWidget = {
    component: BigRibbonWidget,
    extractProps: ({ attrs }) => {
        return {
            text: attrs.title || attrs.text,
            title: attrs.tooltip,
            bgClass: attrs.bg_color,
        };
    },
    supportedAttributes: [
        {
            label: _t("Title"),
            name: "title",
            type: "string",
        },
        {
            label: _t("Background color"),
            name: "bg_color",
            type: "string",
        },
        {
            label: _t("Tooltip"),
            name: "tooltip",
            type: "string",
        },
    ],
};

registry.category("view_widgets").add("big_ribbon", bigRibbonWidget);
