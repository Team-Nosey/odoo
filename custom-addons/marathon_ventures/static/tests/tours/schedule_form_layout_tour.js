/**
 * Tour for the Schedule form layout.
 *
 * The layout is XML plus one JS relocation, and nothing here was covered
 * before. What it proves: the New button is gone, the record name appears
 * once rather than twice, the Details row reads Program / Deal Parent /
 * Status, the header buttons really do end up on the breadcrumb row (the
 * part that cannot be asserted from the arch, since Owl does the moving),
 * and the band they came from stops occupying a row.
 *
 * Driven from tests/test_schedule_form_ui.py.
 */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mv_schedule_form_layout_tour", {
    steps: () => [
        {
            content: "the schedule form mounted",
            trigger: ".o_form_view.mv-deal-redesign",
        },
        {
            content: "no New button on this form",
            trigger: ".o_control_panel",
            run() {
                if (document.querySelector(".o_form_button_create")) {
                    throw new Error("the New button is still rendered");
                }
            },
        },
        {
            // The breadcrumb already carries the name. The banner used to
            // repeat it, so the form opened saying A-0001 twice.
            content: "the record name is not repeated in the sheet",
            trigger: ".mv-deal-banner",
            run() {
                const name = document.querySelector(
                    ".o_last_breadcrumb_item")?.textContent.trim();
                if (!name) {
                    throw new Error("no record name in the breadcrumb");
                }
                const banner = document.querySelector(".mv-deal-banner").textContent;
                if (banner.includes(name)) {
                    throw new Error(`the banner still repeats ${name}`);
                }
            },
        },
        {
            // Its own field label, not a styled caption, so the help text
            // stays reachable.
            content: "Record Type keeps its field label",
            trigger: ".mv-deal-banner .o_field_radio[name='sf_record_type']",
            run() {
                // Must be the FIELD's label, not one of the radio options'.
                // Checking for any <label> in the banner passed while the
                // field was genuinely unlabelled, because every radio option
                // renders a <label> of its own.
                const label = document.querySelector(
                    ".mv-deal-banner label[for='sf_record_type'], "
                    + ".mv-deal-banner .o_form_label");
                if (!label) {
                    throw new Error("Record Type has no field label");
                }
                if (!/record type/i.test(label.textContent)) {
                    throw new Error(
                        `the label reads ${JSON.stringify(label.textContent)}`);
                }
            },
        },
        {
            // A <group name="..."> does not put its name in the DOM - only its
            // class survives compilation - so the row is addressed by class.
            // It is the first .mv-details-row on the Details page.
            content: "Details reads Program, Deal Parent, Status",
            trigger: ".mv-deal-redesign .o_group.mv-details-row",
            run() {
                const row = document.querySelector(
                    ".mv-deal-redesign .o_group.mv-details-row");
                const order = [...row.querySelectorAll(".o_field_widget[name]")]
                    .map((el) => el.getAttribute("name"));
                const expected = ["program", "deal_parent", "status"];
                if (JSON.stringify(order) !== JSON.stringify(expected)) {
                    throw new Error(`fields are ${JSON.stringify(order)}`);
                }
            },
        },
        {
            // The part the arch cannot state: mv_schedule_header.js moves the
            // rendered container up here after every render.
            content: "Save and Cancel Schedule sit on the breadcrumb row",
            trigger: ".o_control_panel_breadcrumbs .mv-schedule-header-actions",
            run() {
                const row = document.querySelector(
                    ".o_control_panel_breadcrumbs .mv-schedule-header-actions");
                const labels = [...row.querySelectorAll("button")]
                    .map((b) => b.textContent.trim());
                for (const wanted of ["Save", "Cancel Schedule"]) {
                    if (!labels.includes(wanted)) {
                        throw new Error(
                            `${wanted} is not on the breadcrumb row: ` +
                            JSON.stringify(labels));
                    }
                }
                // Uncancel takes Cancel's place on a canceled schedule, so it
                // must not be showing on a sold one.
                if (labels.includes("Uncancel Schedule")) {
                    throw new Error("Uncancel Schedule is showing on a sold schedule");
                }
            },
        },
        {
            content: "and the band they came from takes no room",
            trigger: ".o_form_view",
            run() {
                const bands = [...document.querySelectorAll(
                    ".mv-deal-redesign .o_form_statusbar")];
                const showing = bands.filter(
                    (b) => b.getBoundingClientRect().height > 0);
                if (showing.length) {
                    const b = showing[0];
                    throw new Error(
                        "the empty header band still occupies a row: "
                        + `height=${b.getBoundingClientRect().height}, `
                        + `display=${getComputedStyle(b).display}, `
                        + `inline=${JSON.stringify(b.getAttribute("style"))}`);
                }
            },
        },
        {
            // Guards the column split: Days Allowed holds seven tags and the
            // times hold "12:00A", so an even fifth each wrapped the days onto
            // three lines. Compares the rendered columns rather than the CSS,
            // so a change to the grid shows up here.
            content: "Days Allowed is wider than the time columns",
            trigger: ".mv-timing-row .o_field_widget[name='days_allowed']",
            run() {
                const width = (name) => document.querySelector(
                    `.mv-timing-row .o_field_widget[name='${name}']`)
                    .getBoundingClientRect().width;
                const days = width("days_allowed");
                const start = width("start_time");
                const end = width("end_time");
                if (!(days > start * 2 && days > end * 2)) {
                    throw new Error(
                        `days=${Math.round(days)} start=${Math.round(start)} `
                        + `end=${Math.round(end)} - the times did not give up `
                        + "their width");
                }
            },
        },
        {
            content: "the footer is out of the way on a clean record",
            trigger: ".o_form_view",
            run() {
                const footer = document.querySelector(".mv-form-footer");
                if (footer && footer.getBoundingClientRect().height > 0) {
                    throw new Error("the footer shows before anything is edited");
                }
            },
        },
        {
            // Any edit will do - this one is just a plain numeric input, so
            // the step is about the footer appearing, not the widget.
            //
            // Not the "edit" helper: it fires `input`, and the field commits
            // to the record on `change`, so the record never turned dirty and
            // the footer stayed down. Both events go out explicitly, the same
            // way the postlog tour drives its date and select inputs.
            content: "edit something so the footer comes out",
            trigger: ".o_field_widget[name='units_available'] input",
            run() {
                const input = document.querySelector(
                    ".o_field_widget[name='units_available'] input");
                input.value = "7";
                for (const type of ["input", "change"]) {
                    input.dispatchEvent(new Event(type, { bubbles: true }));
                }
            },
        },
        {
            content: "the footer offers Cancel and no second Save",
            trigger: ".o_form_dirty .mv-form-footer",
            run() {
                const footer = document.querySelector(".mv-form-footer");
                const labels = [...footer.querySelectorAll("button, a.btn")]
                    .map((b) => b.textContent.trim());
                if (!labels.includes("Cancel")) {
                    throw new Error(`no Cancel in the footer: ${JSON.stringify(labels)}`);
                }
                if (labels.some((t) => /Save/.test(t))) {
                    throw new Error(
                        `the footer still has a Save button: ${JSON.stringify(labels)}`);
                }
            },
        },
        {
            // Leaves the form clean, which the tour runner insists on - and
            // on the way proves the footer's Cancel still discards now that
            // it is the only button left down there.
            content: "the footer's Cancel discards the edit",
            trigger: ".mv-form-footer .mv_cancel_deal",
            run: "click",
        },
        {
            content: "and the record is clean again",
            trigger: ".o_form_view:not(:has(.o_form_dirty))",
        },
        {
            // Beside the name, not merely somewhere on the row. Appending to
            // the breadcrumb container put the buttons after its me-auto
            // spacer, which pushed them ~300px right of the name while every
            // other assertion here still passed.
            content: "the buttons sit beside the record name",
            trigger: ".o_control_panel_breadcrumbs .mv-schedule-header-actions",
            run() {
                const name = document.querySelector(".o_last_breadcrumb_item");
                const buttons = document.querySelector(
                    ".o_control_panel_breadcrumbs .mv-schedule-header-actions");
                const gap = buttons.getBoundingClientRect().left
                    - name.getBoundingClientRect().right;
                if (gap > 120) {
                    throw new Error(
                        `the buttons are ${Math.round(gap)}px from the name - `
                        + "an auto margin on the row is probably in front of them");
                }
            },
        },
        {
            content: "open the Additional Fields tab",
            trigger: ".o_notebook_headers a:contains('Additional Fields')",
            run: "click",
        },
        {
            // The exact set, not a spot check. The tab used to render every
            // Schedule field not already on Details - 224 of them, nearly all
            // permanently blank - and the point of the change is that it now
            // renders these and nothing else. An exact list is what makes a
            // field creeping back, or a kept one vanishing, fail here.
            content: "Additional Fields holds only the fields people work in",
            trigger: ".o_notebook_content .tab-pane.active .o_field_widget[name]",
            run() {
                const shown = [...document.querySelectorAll(
                    ".o_notebook_content .tab-pane.active .o_field_widget[name]")]
                    .map((el) => el.getAttribute("name"));
                const expected = [
                    "dollars_booked", "capped_dollars", "dollars_canceled",
                    "wo_booked",
                    "wo_30_units", "x30_rate", "capped_units", "locked_units",
                    "units_preempted", "units_aired", "priority",
                    "intacct_si_number", "intacct_cm_number",
                    "intacct_si_number_date_fully_paid",
                    "intacct_si_number_payment_status", "net_total",
                    "netsuite_invoice_number", "netsuite_invoice_url",
                    "performance", "performance_dollars",
                    "additional_intacct_si_number",
                    "additional_intacct_si_number_comments", "invoice_date",
                ];
                const missing = expected.filter((f) => !shown.includes(f));
                const extra = shown.filter((f) => !expected.includes(f));
                if (missing.length || extra.length) {
                    throw new Error(
                        `missing=${JSON.stringify(missing)} `
                        + `extra=${JSON.stringify(extra)}`);
                }
            },
        },
        {
            // Units Aired is the one field rescued from the removals: it is
            // what Run Preemptions produces, and the design dropped it while
            // keeping Units Preempted, which would have left the button's
            // result nowhere on the form.
            content: "Units Aired sits beside Units Preempted",
            trigger: ".o_notebook_content .tab-pane.active .o_field_widget[name='units_aired']",
        },
        {
            // Capped Dollars is a Float where its neighbours are Monetary, so
            // it rendered as a bare number in a column of dollar amounts. The
            // view gives it the currency; this catches the widget being lost.
            content: "every dollar field on the tab shows its currency",
            trigger: ".o_notebook_content .tab-pane.active .o_field_widget[name='capped_dollars']",
            run() {
                for (const name of ["dollars_booked", "capped_dollars",
                                    "dollars_canceled", "wo_booked"]) {
                    const el = document.querySelector(
                        ".o_notebook_content .tab-pane.active "
                        + `.o_field_widget[name='${name}']`);
                    if (!el.textContent.includes("$")) {
                        throw new Error(`${name} renders without a currency`);
                    }
                }
            },
        },
        {
            content: "open the Related tab",
            trigger: ".o_notebook_headers a:contains('Related')",
            run: "click",
        },
        {
            content: "Related lists Spot Data and Prelog Data, and no mirrors",
            trigger: ".mv-related-section__title",
            run() {
                const titles = [...document.querySelectorAll(
                    ".mv-related-section__title")].map((n) => n.textContent.trim());
                const expected = ["Spot Data", "Prelog Data"];
                if (JSON.stringify(titles) !== JSON.stringify(expected)) {
                    throw new Error(`Related shows ${JSON.stringify(titles)}`);
                }
            },
        },
    ],
});


/**
 * A new schedule still opens with the form's New button gone.
 *
 * `create="false"` was added to drop the New button from the control panel,
 * and the risk was that it also blocked the form from opening on an unsaved
 * record - which would break the real creation paths, the Deal form's New
 * Schedule button and the Additional Schedules wizard. Odoo reads that flag
 * only when deciding whether to render the button, so the act_window those
 * two open is unaffected; this asserts it against a running form rather than
 * leaving it to a reading of the source.
 */
registry.category("web_tour.tours").add("mv_new_schedule_form_tour", {
    steps: () => [
        {
            // A schedule-only field, so this cannot pass on some other form
            // that happens to share the mv-deal-redesign styling.
            content: "the schedule form opened on an unsaved record",
            trigger: ".o_form_view.mv-deal-redesign .o_field_widget[name='week']",
        },
        {
            content: "still with no New button",
            trigger: ".o_control_panel",
            run() {
                if (document.querySelector(".o_form_button_create")) {
                    throw new Error("the New button is rendered on a new record");
                }
            },
        },
    ],
});

/**
 * The Schedules list: which columns show, and what the menu offers.
 *
 * The list used to open with seven columns nobody could hide and none of
 * which held a value, and its show/hide menu offered ten fields. It now
 * offers every field the form shows - the Details tab plus Additional
 * Fields - so the menu and the record agree on what a Schedule has.
 */
registry.category("web_tour.tours").add("mv_schedule_list_columns_tour", {
    steps: () => [
        {
            content: "the schedules list rendered",
            trigger: ".o_list_view .o_list_table thead th[data-name='name']",
        },
        {
            // The exact visible set, in order. Alphabetical by label after
            // the record name, which is how the arch declares them and so
            // also how the menu lists them.
            content: "the list opens on the thirteen columns that matter",
            trigger: ".o_list_table thead th[data-name]",
            run() {
                const shown = [...document.querySelectorAll(
                    ".o_list_table thead th[data-name]")]
                    .map((th) => th.dataset.name)
                    .filter((n) => n !== "0");
                const expected = [
                    "name", "kf_account", "kf_advertiser", "deal_parent",
                    "program", "rate", "start_time", "status", "total_dollars",
                    "units_aired", "units_available", "units_preempted", "week",
                ];
                const missing = expected.filter((f) => !shown.includes(f));
                const extra = shown.filter((f) => !expected.includes(f));
                if (missing.length || extra.length) {
                    throw new Error(
                        `missing=${JSON.stringify(missing)} `
                        + `extra=${JSON.stringify(extra)} `
                        + `shown=${JSON.stringify(shown)}`);
                }
            },
        },
        {
            // The seven the generator seeded and nobody could turn off.
            content: "and none of the blank columns it used to force on you",
            trigger: ".o_list_table thead",
            run() {
                const gone = ["adus_estimated", "adus_generated", "access_code",
                              "account_advertiser_program", "account_advertiser",
                              "account_brand_program",
                              "actual_total_000_primary_demo"];
                const still = gone.filter((f) => document.querySelector(
                    `.o_list_table thead th[data-name='${f}']`));
                if (still.length) {
                    throw new Error(`still forced on: ${JSON.stringify(still)}`);
                }
            },
        },
        {
            content: "open the show/hide columns menu",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            // The menu is portalled out of the list and rendered at the end of
            // the body, so it cannot be reached through the toggle's own
            // container.
            content: "it offers every field the form shows",
            trigger: ".o-dropdown--menu .o-checkbox input[type=checkbox]",
            run() {
                const boxes = [...document.querySelectorAll(
                    ".o-dropdown--menu .o-checkbox input[type=checkbox]")];
                // 43 form fields. name is not optional - it is the row's
                // identity and hiding every column would leave nothing to
                // click - and currency_id and test carry no column at all.
                if (boxes.length !== 43) {
                    throw new Error(`the menu offers ${boxes.length}, expected 43`);
                }
                const checked = boxes.filter((b) => b.checked).length;
                if (checked !== 12) {
                    throw new Error(`${checked} are checked, expected 12`);
                }
            },
        },
    ],
});
