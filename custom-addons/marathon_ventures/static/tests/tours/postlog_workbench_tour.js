/**
 * Tour for the Postlog Workbench client action.
 *
 * Proves the OWL component mounts, the filters drive a real RPC, and a matched
 * row reaches the DOM. Driven from tests/test_postlog_workbench_ui.py, which
 * creates the "UI Test Network" fixtures this tour expects.
 */
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

registry.category("web_tour.tours").add("postlog_workbench_tour", {
    steps: () => [
        {
            content: "the workbench mounted",
            trigger: ".mv-fuzzy__page-title:contains('Postlog Workbench')",
        },
        {
            content: "the dropped Version filter is not rendered",
            trigger: ".mv-fuzzy__filter-grid",
            run() {
                const text = document.querySelector(".mv-fuzzy__filter-grid").textContent;
                if (text.includes("Version")) {
                    throw new Error("the Version filter is still rendered");
                }
            },
        },
        {
            content: "the dropped Removed tab is not rendered",
            trigger: ".mv-fuzzy",
            run() {
                const tabs = document.querySelector(".mv-fuzzy__tabs");
                if (tabs && /Removed/.test(tabs.textContent)) {
                    throw new Error("the Removed tab is still rendered");
                }
            },
        },
        {
            content: "pick the program",
            trigger: ".mv-fuzzy__filter-grid select",
            // The generic "select" helper matches an option by its VALUE, and
            // these options are keyed by program id with the name as the label.
            // Find the option by its text and set the value explicitly.
            run() {
                const select = document.querySelector(".mv-fuzzy__filter-grid select");
                const option = [...select.options].find(
                    (o) => o.textContent.trim() === "UI Test Network");
                if (!option) {
                    throw new Error("UI Test Network is not in the Program dropdown");
                }
                select.value = option.value;
                select.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "set the broadcast week",
            trigger: ".mv-fuzzy__filter-grid input[type=date]",
            // The generic "edit" helper types into the field character by
            // character, which a native date input rejects. Set the value and
            // fire the change the component listens for.
            run() {
                const input = document.querySelector(
                    ".mv-fuzzy__filter-grid input[type=date]");
                input.value = "2026-07-27";
                input.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "run the query",
            trigger: ".mv-fuzzy__filter-actions .btn-primary",
            run: "click",
        },
        {
            content: "the fixture row rendered",
            trigger: "td:contains('UI Fixture Product')",
        },
        {
            content: "the deal number rendered",
            trigger: ".mv-fuzzy:contains('UIT-1')",
        },
        {
            // The Schedule column shows attachments only, so an unmatched row
            // leaves it blank. What the list surfaces for such a row is the
            // suggestion count in Info; the schedule itself is in the drawer,
            // asserted further down.
            content: "an unmatched row advertises its suggestions in Info",
            trigger: ".mv-fuzzy__table .mv-fuzzy__reason:contains('suggestion')",
        },
        {
            // The badge reports the stored code and nothing else. "Fuzzy
            // Suggestion" here is what made an exact match look unmatched.
            content: "the status badge reads Unmatched, not Fuzzy Suggestion",
            trigger: ".mv-fuzzy__table .mv-postlog-status--unmatched:contains('Unmatched')",
        },
        {
            // Renamed columns and the moved Schedule column, asserted so a
            // rename cannot silently revert.
            content: "Postlog is the third column",
            trigger: ".mv-fuzzy__table thead th:nth-child(3):contains('Postlog')",
        },
        {
            content: "Schedule sits directly beside it",
            trigger: ".mv-fuzzy__table thead th:nth-child(4):contains('Schedule')",
        },
        {
            content: "the Info column replaced Reason",
            trigger: ".mv-fuzzy__table thead th:contains('Info')",
        },
        {
            content: "the tab reads Suggestions",
            trigger: ".mv-fuzzy__tabs button:contains('Suggestions')",
        },
        {
            content: "Import is available from the workbench",
            trigger: ".mv-fuzzy__filter-actions button:contains('Import')",
        },
        {
            content: "Refresh sits with the table, not the filter bar",
            trigger: ".mv-fuzzy__bulk-actions button:contains('Refresh')",
        },
        {
            // Everything below this point is the review drawer. Without these
            // steps the tour only proved the list renders, and the drawer - the
            // ranked candidate table, the diff highlighting, the Attach buttons -
            // had no coverage at all.
            content: "open the review drawer",
            trigger: ".mv-fuzzy__table .btn:contains('Review')",
            run: "click",
        },
        {
            content: "the drawer shows the ranked candidate list",
            trigger: ".mv-fuzzy__drawer:contains('Possible schedules')",
        },
        {
            content: "the Postlog Data card is the pinned subject of the comparison",
            trigger: ".mv-postlog-sched__subject:contains('Postlog Data')",
        },
        {
            content: "the suggestion is rank 1",
            trigger: ".mv-postlog-sched__row--suggested .mv-postlog-sched__rank--first:contains('1')",
        },
        {
            content: "the suggestion is labelled Suggested",
            trigger: ".mv-postlog-sched__row--suggested:contains('Suggested')",
        },
        {
            content: "the candidate carries an Attach action",
            trigger: ".mv-postlog-sched__row--suggested .mv-postlog-sched__col-action .btn:contains('Attach')",
        },
        {
            content: "the drawer knows where it sits in the page",
            trigger: ".mv-postlog-drawer-nav__position:contains('of')",
        },
        {
            content: "stepping to the next row keeps the drawer open",
            trigger: ".mv-postlog-drawer-nav button[title='Next row']:not([disabled])",
            run: "click",
        },
        {
            // The position counter is the claim: the drawer is still open AND it
            // moved. Asserting on drawer content instead would depend on the
            // next row happening to have a suggestion.
            content: "the drawer moved to the second row without closing",
            trigger: ".mv-postlog-drawer-nav__position:contains('2 of 2')",
        },
        {
            content: "and back",
            trigger: ".mv-postlog-drawer-nav button[title='Previous row']:not([disabled])",
            run: "click",
        },
        {
            content: "back on the first row",
            trigger: ".mv-postlog-drawer-nav__position:contains('1 of 2')",
        },
        {
            content: "the Rotation column rendered",
            trigger: ".mv-postlog-sched__row--suggested .mv-postlog-sched__match",
        },
        {
            // Last, deliberately: Refresh attaches anything that now matches
            // cleanly, and an attached row shows its attachment instead of a
            // ranked candidate list. Every assertion about that list has to
            // happen before this runs.
            content: "re-check from inside the drawer",
            trigger: ".mv-postlog-drawer-nav button[title^='Re-check']:not([disabled])",
            run: "click",
        },
        {
            // The row matched cleanly, so Refresh attached it - and the drawer
            // stays on THAT row to show the result, rather than swapping in
            // whatever now occupies its old position.
            content: "the drawer still shows the row you were on, now attached",
            trigger: ".mv-fuzzy__drawer:contains('Attached Schedule')",
        },
        {
            // The tour runs on the All tab, where a matched row is still listed,
            // so the counter keeps a real position. "not in view" only appears
            // on a filtered tab once the row leaves it - not reachable here
            // without another filter step, so it stays unasserted rather than
            // asserted loosely.
            content: "and the position counter is still meaningful",
            trigger: ".mv-postlog-drawer-nav__position:contains('of')",
        },

        // ---- the background import lifecycle -------------------------------
        // Everything below repoints the filters at a job that owns no rows, so
        // no step may follow it.
        //
        // The wizard needs a real file upload, which a tour cannot synthesise.
        // So the job is created out of band *while the wizard is open* - after
        // onImport has captured the previous job id, which is the seam that
        // makes _watchImportJob pick it up. Everything downstream of that seam
        // is the real code path: the cleared table, the panel, the disabled
        // toolbar, and the reload on completion.
        {
            content: "leave the drawer",
            trigger: ".mv-postlog-drawer-nav button[title='Close']",
            run: "click",
        },
        {
            content: "open the upload wizard",
            trigger: ".mv-fuzzy__filter-actions button:contains('Import')",
            run: "click",
        },
        {
            content: "queue a job behind the open wizard",
            trigger: ".modal-dialog footer button:contains('Cancel')",
            async run() {
                const programs = await rpc("/web/dataset/call_kw", {
                    model: "mv.programs",
                    method: "search_read",
                    args: [[["name", "=", "UI Test Network"]], ["id"]],
                    kwargs: { limit: 1 },
                });
                const created = await rpc("/web/dataset/call_kw", {
                    model: "mv.postlog_import_job",
                    method: "create",
                    args: [{
                        program_id: programs[0].id,
                        import_week: "2026-07-27",
                        upload_file: "eA==",
                        upload_filename: "tour.csv",
                        file_checksum: "tour-checksum",
                        state: "queued",
                    }],
                    kwargs: {},
                });
                window.__tourImportJobId = Array.isArray(created) ? created[0] : created;
            },
        },
        {
            content: "close the wizard, which is what starts the watch",
            trigger: ".modal-dialog footer button:contains('Cancel')",
            run: "click",
        },
        {
            content: "the waiting panel replaces the previous view",
            trigger: ".mv-postlog-import-wait:contains('Waiting for the import')",
        },
        {
            content: "and the previous rows are gone, not merely captioned",
            trigger: "body:not(:has(.mv-fuzzy__results))",
        },
        {
            content: "a second import cannot be queued on top of the first",
            trigger: ".mv-fuzzy__filter-actions button:contains('Import')[disabled]",
        },
        {
            content: "finish the job",
            trigger: ".mv-postlog-import-wait",
            async run() {
                await rpc("/web/dataset/call_kw", {
                    model: "mv.postlog_import_job",
                    method: "write",
                    args: [[window.__tourImportJobId], {
                        state: "completed",
                        total_row_count: 1,
                        matched_count: 1,
                        unmatched_count: 0,
                        error_count: 0,
                    }],
                    kwargs: {},
                });
            },
        },
        {
            content: "the panel releases and the results section comes back",
            trigger: ".mv-fuzzy__results",
        },
        {
            content: "and the waiting panel is gone",
            trigger: "body:not(:has(.mv-postlog-import-wait))",
        },
    ],
});
