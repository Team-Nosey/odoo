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
            // This step has tracked what postlog does and does not have
            // twice now - it guarded the absence of Removed, then of
            // Overruns, and both eventually arrived. It asserts the whole
            // set instead, so the next addition or removal shows up as a
            // failure here rather than being noticed months later.
            //
            // It has to sit after the first query: the tab nav renders
            // only once hasFiltered is true. The guards it replaced were
            // null-safe negative checks, so they passed on the empty
            // welcome screen and never needed a result.
            content: "the tab set is exactly what postlog supports",
            trigger: ".mv-fuzzy__tabs",
            run() {
                const labels = [...document.querySelectorAll(".mv-fuzzy__tabs button")]
                    .map((b) => b.textContent.replace(/[0-9]+/g, "").trim());
                const expected = ["All", "Matched", "Unmatched", "Suggestions",
                                  "No Suggestion", "Removed", "Overruns"];
                if (JSON.stringify(labels) !== JSON.stringify(expected)) {
                    throw new Error(`tabs are ${JSON.stringify(labels)}`);
                }
            },
        },
        {
            content: "the deal number rendered",
            trigger: ".mv-fuzzy:contains('UIT-1')",
        },
        {
            // The fixture rows air at 09:30:00 and 10:30:00. Standard time is
            // what the uploaded files carry, so it is what the column shows.
            content: "air time reads as standard time, not 24-hour",
            trigger: ".mv-fuzzy__table tbody:contains('09:30:00 AM')",
        },
        {
            content: "and 24-hour is nowhere in the column",
            trigger: ".mv-fuzzy__table",
            run() {
                const cells = [...document.querySelectorAll(".mv-fuzzy__table tbody tr")]
                    .map((tr) => tr.children[5]?.textContent || "");
                const military = cells.filter((t) => /·\s*(1[3-9]|2[0-3]):/.test(t));
                if (military.length) {
                    throw new Error(`24-hour air times still rendered: ${military}`);
                }
            },
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
        // ---- remove / restore ----------------------------------------------
        {
            // setRemoved goes through window.confirm, which a headless browser
            // cannot click. Stubbed to accept, but recording what it was asked
            // - the wording is the whole safeguard, so the tour checks it.
            content: "accept confirmations, and remember what they said",
            trigger: ".mv-fuzzy__table",
            run() {
                window.__tourConfirms = [];
                window.confirm = (message) => {
                    window.__tourConfirms.push(message);
                    return true;
                };
            },
        },
        {
            content: "select every row on the page",
            trigger: ".mv-fuzzy__table thead input[type=checkbox]",
            run: "click",
        },
        {
            content: "remove them from reconciliation",
            trigger: ".mv-fuzzy__bulk-actions button:contains('Remove')",
            run: "click",
        },
        {
            content: "the confirmation warned that the schedule would be cleared",
            trigger: ".mv-fuzzy__tabs",
            run() {
                const asked = window.__tourConfirms || [];
                if (!asked.some((m) => m.includes("Schedule ID will be cleared"))) {
                    throw new Error(
                        `Remove did not warn about clearing the schedule: ${JSON.stringify(asked)}`
                    );
                }
            },
        },
        {
            content: "they left All and landed in Removed",
            trigger: ".mv-fuzzy__tabs button:contains('Removed') span:contains('2')",
        },
        {
            content: "All is empty now",
            trigger: ".mv-fuzzy__tabs button:contains('All') span:contains('0')",
        },
        {
            content: "open the Removed tab",
            trigger: ".mv-fuzzy__tabs button:contains('Removed')",
            run: "click",
        },
        {
            content: "and the badge says Removed",
            trigger: ".mv-fuzzy__table .mv-fuzzy__status--removed:contains('Removed')",
        },
        {
            content: "Remove is not offered here; Restore is",
            trigger: ".mv-fuzzy__bulk-actions button:contains('Restore')",
        },
        {
            content: "select them again",
            trigger: ".mv-fuzzy__table thead input[type=checkbox]",
            run: "click",
        },
        {
            content: "restore them",
            trigger: ".mv-fuzzy__bulk-actions button:contains('Restore')",
            run: "click",
        },
        {
            content: "Removed is empty again",
            trigger: ".mv-fuzzy__tabs button:contains('Removed') span:contains('0')",
        },
        {
            // Restore re-runs the matcher with attach=True, and the two fixture
            // rows split exactly on the rule: the first is clean on all four
            // checks and comes back attached, the second aired 30 minutes past
            // its rotation - inside the fuzzy buffer, so not clean - and comes
            // back as a suggestion for review instead.
            content: "restoring re-attached the clean row",
            trigger: ".mv-fuzzy__tabs button:contains('Matched') span:contains('1')",
        },
        {
            content: "and left the 30-minutes-off row as a suggestion",
            trigger: ".mv-fuzzy__tabs button:contains('Suggestions') span:contains('1')",
        },

        // ---- overruns --------------------------------------------------------
        // One row is already attached from the drawer-refresh block, against a
        // schedule that sold one unit. Attaching the second puts two spots on
        // it, which is the overrun.
        {
            // Restore left us on the Removed tab, which is empty now - so there
            // is no table to select from until we go back to All.
            content: "back to All, where the rows are",
            trigger: ".mv-fuzzy__tabs button:contains('All')",
            run: "click",
        },
        {
            content: "select every row on the page",
            trigger: ".mv-fuzzy__table thead input[type=checkbox]",
            run: "click",
        },
        {
            // The second row is 30 minutes outside its rotation, so this asks
            // for confirmation - accepted by the stub installed above.
            content: "attach the remaining suggestion to the same schedule",
            trigger: ".mv-fuzzy__bulk-actions button:contains('Attach Suggested')",
            run: "click",
        },
        {
            content: "two spots on a one-unit schedule is an overrun",
            trigger: ".mv-fuzzy__tabs button:contains('Overruns') span:contains('2')",
        },
        {
            content: "and they leave Matched rather than hiding in it",
            trigger: ".mv-fuzzy__tabs button:contains('Matched') span:contains('0')",
        },
        {
            content: "open the Overruns tab",
            trigger: ".mv-fuzzy__tabs button:contains('Overruns')",
            run: "click",
        },
        {
            content: "the status badge reads Overrun",
            trigger: ".mv-fuzzy__table .mv-fuzzy__status--overrun:contains('Overrun')",
        },
        {
            content: "the schedule carries a +1 badge - units over, not rows",
            trigger: ".mv-fuzzy__table .mv-fuzzy__overrun-badge:contains('+1')",
        },
        {
            content: "and Info names the schedule's figures",
            trigger: ".mv-fuzzy__table .mv-fuzzy__reason:contains('1 unit(s) but 2 postlog(s)')",
        },
        {
            content: "open the drawer on an overrun row",
            trigger: ".mv-fuzzy__table tbody tr:first-child button:contains('Review')",
            run: "click",
        },
        {
            content: "the drawer explains the overrun",
            trigger: ".mv-fuzzy__overrun-panel:contains('Units sold')",
        },
        {
            content: "and lists both spots on the schedule",
            trigger: ".mv-fuzzy__overrun-list li:nth-child(2)",
        },
        {
            content: "with Remove offered where the problem is stated",
            trigger: ".mv-fuzzy__overrun-panel button:contains('Remove this spot')",
        },
        {
            content: "leave the drawer again",
            trigger: ".mv-postlog-drawer-nav button[title='Close']",
            run: "click",
        },
        {
            content: "back to All",
            trigger: ".mv-fuzzy__tabs button:contains('All')",
            run: "click",
        },

        // ---- run preemptions -------------------------------------------------
        // The fixture schedule sold one unit and has two spots attached, so a
        // run writes units_preempted = -1. Negatives are the point: units_aired
        // is available - preempted, so -1 makes it report the 2 that aired
        // rather than the 1 that was sold.
        {
            content: "run preemptions for the week",
            trigger: ".mv-fuzzy__bulk-actions button:contains('Run Preemptions')",
            run: "click",
        },
        {
            content: "it asked before writing, and said what it would assert",
            trigger: ".mv-fuzzy__bulk-actions",
            run() {
                const asked = window.__tourConfirms || [];
                if (!asked.some((m) => m.includes("marked fully preempted"))) {
                    throw new Error(
                        `Run Preemptions did not preview the full-preemption count: ${JSON.stringify(asked)}`
                    );
                }
            },
        },
        {
            content: "and reported what it wrote",
            trigger: ".o_notification:contains('Preemptions run on')",
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
