/** @odoo-module **/

import {download} from "@web/core/network/download";
import {registry} from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

registry
    .category("ir.actions.report handlers")
    .add("xlsx_handler", async function (action, options, env) {
        if (action.report_type === "xlsx") {
            const type = action.report_type;
            let url = `/report/${type}/${action.report_name}`;
            const actionContext = action.context || {};
            if (action.data && JSON.stringify(action.data) !== "{}") {
                // Build a query string with `action.data` (it's the place where reports
                // using a wizard to customize the output traditionally put their options)
                const action_options = encodeURIComponent(JSON.stringify(action.data));
                const context = encodeURIComponent(JSON.stringify(actionContext));
                url += `?options=${action_options}&context=${context}`;
            } else {
                if (actionContext.active_ids) {
                    url += `/${actionContext.active_ids.join(",")}`;
                }
                if (type === "xlsx") {
                    const context = encodeURIComponent(
                        JSON.stringify(env.services.user.context)
                    );
                    url += `?context=${context}`;
                }
            }
            env.services.ui.block();
            try {
                await download({
                    url: "/report/download",
                    data: {
                        data: JSON.stringify([url, action.report_type]),
                        context: JSON.stringify(env.services.user.context),
                    },
                });
            } finally {
                env.services.ui.unblock();
            }
            const onClose = options.onClose;
            if (action.close_on_report_download) {
                return env.services.action.doAction(
                    {type: "ir.actions.act_window_close"},
                    {onClose}
                );
            } else if (onClose) {
                onClose();
            }
            return Promise.resolve(true);
        }
        return Promise.resolve(false);
    });
export class BigRibbonWidget extends Component {
    static template = "web.Ribbon"; // Create a new template (see note below)
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
    