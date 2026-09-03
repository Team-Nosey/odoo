/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";

export class MvPostlogMatching extends Component {
    static template = "marathon_ventures.MvPostlogMatching";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        onWillUnmount(() => { this.isUnmounted = true; });
        this.requestId = 0;
        // Set on unmount so the import poll below stops rather than writing to
        // a dead component.
        this.isUnmounted = false;
        this.state = useState({
            loaded: false,
            querying: false,
            mutating: false,
            exporting: false,
            hasFiltered: false,
            programs: [],
            latestUpload: false,
            pageSize: 200,
            timeBufferMinutes: 120,
            filters: { programId: false, weekStart: "", importJobId: false },
            activeTab: "all",
            counts: { all: 0, matched: 0, unmatched: 0, suggestions: 0,
                      no_suggestion: 0, removed: 0 },
            searchTerm: "",
            airDate: "",
            issueFilter: "",
            refreshing: false,
            importJob: false,
            drawerAnchor: 0,
            sortBy: "air_date",
            sortDirection: "asc",
            rows: [],
            total: 0,
            offset: 0,
            page: 0,
            pages: 0,
            selectedRows: {},
            selectAllMatching: false,
            excludedRows: {},
            drawerRow: false,
            manualSchedule: "",
        });

        onWillStart(async () => {
            const options = await this.orm.call("mv.spot_data", "fuzzy_match_get_options", []);
            this._setOptions(options, true);
            const latest = this.state.latestUpload;
            if (latest) {
                this.state.filters.programId = latest.program_id;
                this.state.filters.weekStart = latest.week_start;
                this.state.filters.importJobId = latest.id;
                await this._loadResults();
            }
            this.state.loaded = true;
        });
    }

    _setOptions(options, includeLatest = false) {
        options = options || {};
        this.state.programs = options.programs || this.state.programs;
        this.state.pageSize = options.page_size || 200;
        this.state.timeBufferMinutes = options.time_buffer_minutes || 120;
        if (includeLatest) {
            this.state.latestUpload = options.latest_upload || false;
        }
    }

    _clearResults() {
        this.requestId += 1;
        this.state.hasFiltered = false;
        this.state.rows = [];
        this.state.total = 0;
        this.state.offset = 0;
        this._resetSelection();
        this.state.drawerRow = false;
    }

    async onProgramChange(ev) {
        this._clearResults();
        this.state.filters.programId = Number(ev.target.value) || false;
        this.state.filters.importJobId = false;
    }

    async onWeekChange(ev) {
        this._clearResults();
        this.state.filters.weekStart = ev.target.value;
        this.state.filters.importJobId = false;
    }

    _filtersAreValid() {
        const filters = this.state.filters;
        if (filters.weekStart) {
            const date = new Date(`${filters.weekStart}T12:00:00`);
            if (Number.isNaN(date.getTime()) || date.getDay() !== 1) {
                this.notification.add("Week must be the Monday that starts the broadcast week.", { type: "warning" });
                return false;
            }
        }
        return true;
    }

    async onFilter() {
        if (!this._filtersAreValid()) return;
        this.state.offset = 0;
        this._resetSelection();
        await this._loadResults();
    }

    async onSearchKeydown(ev) {
        if (ev.key === "Enter") await this.onFilter();
    }

    async setTab(tab) {
        if (this.state.querying || tab === this.state.activeTab) return;
        this.state.activeTab = tab;
        this.state.offset = 0;
        this._resetSelection();
        this.state.drawerRow = false;
        await this._loadResults();
    }

    _queryArgs() {
        const f = this.state.filters;
        return [
            f.programId || false, f.weekStart || false, this.state.offset,
            this.state.pageSize, this.state.activeTab, this.state.searchTerm,
            this.state.airDate || false, this.state.issueFilter, this.state.sortBy,
            f.importJobId || false, this.state.sortDirection,
        ];
    }

    async _loadResults() {
        const requestId = ++this.requestId;
        this.state.querying = true;
        try {
            const result = await this.orm.call("mv.spot_data", "fuzzy_match_search", this._queryArgs());
            if (requestId !== this.requestId) return;
            this.state.rows = result.rows || [];
            this.state.total = result.total || 0;
            this.state.offset = result.offset || 0;
            this.state.page = result.page || 0;
            this.state.pages = result.pages || 0;
            this.state.counts = result.counts || this.state.counts;
            this.state.hasFiltered = true;
        } finally {
            if (requestId === this.requestId) this.state.querying = false;
        }
    }

    _resetSelection() {
        this.state.selectedRows = {};
        this.state.selectAllMatching = false;
        this.state.excludedRows = {};
    }

    get selectedCount() {
        return this.state.selectAllMatching
            ? Math.max(this.state.total - Object.keys(this.state.excludedRows).length, 0)
            : Object.keys(this.state.selectedRows).length;
    }
    get visibleRangeStart() { return this.state.total ? this.state.offset + 1 : 0; }
    get visibleRangeEnd() { return Math.min(this.state.offset + this.state.pageSize, this.state.total); }
    get allPageSelected() {
        return Boolean(this.state.rows.length) && this.state.rows.every((row) => this.isSelected(row));
    }
    get canSelectAllMatching() {
        return !this.state.selectAllMatching && this.allPageSelected && this.state.total > this.state.rows.length;
    }

    isSelected(row) {
        return this.state.selectAllMatching
            ? !this.state.excludedRows[row.id]
            : Boolean(this.state.selectedRows[row.id]);
    }
    toggleRow(row, ev) {
        if (this.state.selectAllMatching) {
            if (ev.target.checked) delete this.state.excludedRows[row.id];
            else this.state.excludedRows[row.id] = true;
        } else if (ev.target.checked) {
            this.state.selectedRows[row.id] = true;
        } else {
            delete this.state.selectedRows[row.id];
        }
    }
    toggleAll(ev) {
        if (this.state.selectAllMatching && !ev.target.checked) {
            this._resetSelection();
            return;
        }
        for (const row of this.state.rows) {
            if (ev.target.checked) {
                delete this.state.excludedRows[row.id];
                this.state.selectedRows[row.id] = true;
            } else {
                delete this.state.selectedRows[row.id];
            }
        }
    }
    selectEveryMatchingRow() {
        this.state.selectAllMatching = true;
        this.state.selectedRows = {};
        this.state.excludedRows = {};
    }
    clearSelection() { this._resetSelection(); }
    _selectionPayload(row = false) {
        if (row) return { all_matching: false, ids: [row.id], excluded_ids: [] };
        return this.state.selectAllMatching
            ? { all_matching: true, ids: [], excluded_ids: Object.keys(this.state.excludedRows).map(Number) }
            : { all_matching: false, ids: Object.keys(this.state.selectedRows).map(Number), excluded_ids: [] };
    }

    _bulkArgs(actionName, row = false, confirmedFuzzy = false) {
        const f = this.state.filters;
        return [
            actionName, this._selectionPayload(row), f.programId || false,
            f.weekStart || false, this.state.activeTab,
            this.state.searchTerm, this.state.airDate || false,
            this.state.issueFilter, this.state.sortBy, f.importJobId || false,
            confirmedFuzzy, this.state.sortDirection,
        ];
    }

    async attachSuggested() {
        if (!this.selectedCount) {
            this.notification.add("Select at least one Postlog row.", { type: "info" });
            return;
        }
        await this._runBulkAttach(false);
    }

    async attachOneSuggestion(row) {
        await this._runBulkAttach(row);
    }

    async _runBulkAttach(row = false, confirmedFuzzy = false) {
        this.state.mutating = true;
        try {
            let result = await this.orm.call(
                "mv.spot_data", "fuzzy_workbench_bulk_action",
                this._bulkArgs("attach", row, confirmedFuzzy)
            );
            if (result.requires_confirmation) {
                this.state.mutating = false;
                const warning = `${result.fuzzy} of ${result.attachable} attachable suggestion(s) are fuzzy or contain a mismatch. Attach them anyway?`;
                if (!window.confirm(warning)) return;
                this.state.mutating = true;
                result = await this.orm.call(
                    "mv.spot_data", "fuzzy_workbench_bulk_action",
                    this._bulkArgs("attach", row, true)
                );
            }
            this.notification.add(result.message, { type: result.attached ? "success" : "info" });
            this._resetSelection();
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    async _applySchedules(payload) {
        const f = this.state.filters;
        this.state.mutating = true;
        try {
            const result = await this.orm.call("mv.spot_data", "fuzzy_match_apply", [
                payload, Number(f.programId), f.weekStart,
            ]);
            this.notification.add(result.message, { type: "success" });
            this._resetSelection();
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    /** Remove rows from reconciliation, or restore them.
     *
     *  Removing clears the attached schedule, which the confirmation states
     *  before it happens: a duplicate that keeps its attachment still
     *  reconciles, so the clear is the point rather than a side effect.
     */
    async setRemoved(removed, row = false) {
        const count = row ? 1 : this.selectedCount;
        if (!count) {
            this.notification.add("Select at least one Postlog row.", { type: "info" });
            return;
        }
        const question = removed
            ? `Remove ${count} row(s)? Any attached Schedule ID will be cleared.`
            : `Restore ${count} row(s)? Matching will be re-run.`;
        if (!window.confirm(question)) return;
        this.state.mutating = true;
        try {
            const result = await this.orm.call(
                "mv.spot_data", "fuzzy_workbench_bulk_action",
                this._bulkArgs(removed ? "remove" : "unremove", row)
            );
            this.notification.add(result.message, { type: "success" });
            this._resetSelection();
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    async deleteSelected(row = false) {
        const count = row ? 1 : this.selectedCount;
        if (!count) {
            this.notification.add("Select at least one Postlog row.", { type: "info" });
            return;
        }
        if (!window.confirm(`Permanently delete ${count} Postlog row(s)? This cannot be undone.`)) return;
        this.state.mutating = true;
        try {
            const result = await this.orm.call(
                "mv.spot_data", "fuzzy_workbench_bulk_action",
                this._bulkArgs("delete", row)
            );
            this.notification.add(result.message, { type: "success" });
            this._resetSelection();
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    /** Re-run matching for the unmatched rows of the selected Program/week.
     *  Stored matching does not self-heal, so this is how a Schedule corrected
     *  after import gets picked up. Unmatched-only, so it cannot undo an
     *  attachment someone made by hand. */
    /** Open the Postlog upload wizard without leaving the workbench.
     *
     *  The wizard closes as soon as the job is QUEUED, not when it is done - the
     *  import runs in the background and the cron polls every minute, so there
     *  can be a minute of nothing before rows appear. Reloading on close simply
     *  showed an empty table, which reads as a failed import. So we watch the
     *  job instead and load when it finishes.
     */
    async onImport() {
        const latest = await this.orm.search("mv.postlog_import_job", [], {
            limit: 1, order: "id desc",
        });
        const previousId = latest.length ? latest[0] : 0;
        await this.action.doAction(
            "marathon_ventures.action_open_postlog_upload_wizard",
            // Braces on purpose: the callback must return undefined, not the
            // poll promise. Odoo awaits whatever onClose returns before tearing
            // the dialog down, so returning the promise left the wizard on
            // screen - and unclosable - for the whole poll.
            { onClose: () => { this._watchImportJob(previousId); } },
        );
    }

    /** Poll the job created by the wizard until it finishes, then load it.
     *  `previousId` is the newest job from before the wizard opened, so a
     *  cancelled wizard (which creates nothing) is a no-op. */
    /** True for the whole life of a watched job - queued, running, and through
     *  the reload that follows it. Keyed on the job's presence rather than its
     *  state on purpose: state flips to "completed" before the new rows have
     *  been fetched, and releasing the panel there would flash an empty table
     *  with zeroed tab counts. _watchImportJob clears the job last. */
    get importInFlight() {
        return Boolean(this.state.importJob);
    }

    /** Drop the on-screen results while an import is in flight.
     *
     *  Also drops the selection: "select all matching" resolves server-side at
     *  click time, so a selection made against the old view would silently
     *  resolve against the new one.
     */
    clearResultsForImport() {
        this.closeDrawer();
        Object.assign(this.state, {
            rows: [],
            total: 0,
            offset: 0,
            page: 0,
            pages: 0,
            counts: {
                all: 0, matched: 0, unmatched: 0, suggestions: 0,
                no_suggestion: 0, removed: 0,
            },
            selectedRows: {},
            selectAllMatching: false,
            excludedRows: {},
        });
    }

    async _watchImportJob(previousId) {
        const created = await this.orm.searchRead(
            "mv.postlog_import_job", [["id", ">", previousId]], ["state"],
            { limit: 1, order: "id desc" },
        );
        if (!created.length) {
            return;                       // wizard cancelled - nothing queued
        }
        const jobId = created[0].id;
        // Hide the previous view for the duration. The week an upload lands in
        // is detected from the file, not chosen in the wizard, so there is no
        // way to know whether the rows on screen are about to be replaced -
        // and a table captioned "2184 rows" under a banner reading "Import
        // running" invites reading the old upload as the new one's result.
        this.clearResultsForImport();
        const FIELDS = ["state", "total_row_count", "matched_count",
                        "unmatched_count", "error_count", "failure_message",
                        "program_id", "import_week"];
        // The cron runs every minute, so the job can sit queued that long before
        // it even starts. Wait well past that before giving up.
        const deadline = Date.now() + 5 * 60 * 1000;
        while (!this.isUnmounted && Date.now() < deadline) {
            const [job] = await this.orm.read("mv.postlog_import_job", [jobId], FIELDS);
            this.state.importJob = job;
            if (job.state === "completed" || job.state === "failed") {
                break;
            }
            await new Promise((resolve) => setTimeout(resolve, 3000));
        }
        if (this.isUnmounted) {
            return;
        }
        const job = this.state.importJob;
        if (job && job.state === "completed") {
            this.notification.add(
                `Import finished: ${job.total_row_count} row(s), ` +
                `${job.matched_count} matched, ${job.unmatched_count} unmatched.`,
                { type: "success" },
            );
            // Point the filters at what was just imported. Without this the
            // page shows the new rows while the filter bar still reads "All
            // Programs" with no week - and Refresh, which reads those filters,
            // would run unscoped.
            if (job.program_id) {
                this.state.filters.programId = job.program_id[0];
            }
            if (job.import_week) {
                this.state.filters.weekStart = job.import_week;
            }
            this.state.filters.importJobId = jobId;
            await this._loadResults();
        } else if (job && job.state === "failed") {
            this.notification.add(job.failure_message || "The import failed.",
                                  { type: "danger" });
            // The view was cleared when the job was queued, so every way out of
            // this watch has to put something back. Without this a failed or
            // slow import left an empty table with zeroed tab counts and no
            // explanation - which reads as "the week is gone".
            await this._loadResults();
        } else {
            this.notification.add(
                "The import is still running. Press View Postlog Data when it finishes.",
                { type: "info" },
            );
            await this._loadResults();
        }
        this.state.importJob = false;
    }

    async onRefresh() {
        const f = this.state.filters;
        this.state.refreshing = true;
        try {
            const result = await this.orm.call("mv.spot_data", "fuzzy_match_refresh", [
                f.programId || false, f.weekStart || false, f.importJobId || false,
            ]);
            this.notification.add(result.message, {
                type: result.attached ? "success" : "info",
            });
            await this._loadResults();
        } finally {
            this.state.refreshing = false;
        }
    }

    async detachSchedule(row) {
        if (!window.confirm(`Detach ${row.attached?.name || "the schedule"} from this Postlog row?`)) return;
        const f = this.state.filters;
        this.state.mutating = true;
        try {
            const result = await this.orm.call("mv.spot_data", "fuzzy_match_detach", [[
                row.id,
            ], f.programId || false, f.weekStart || false, f.importJobId || false]);
            this.notification.add(result.message, { type: "success" });
            this.state.drawerRow = false;
            await this._loadResults();
        } finally { this.state.mutating = false; }
    }

    async attachAlternative(row, alt) {
        // Choosing a runner-up over the ranked suggestion is a deliberate
        // override, so it goes through the same confirmed_override path as a
        // manual attach and is recorded in the audit trail as such.
        const replacing = row.status === "matched";
        if (!window.confirm(
            `${replacing ? "Replace the current schedule with" : "Attach"} ${alt.name}?`
        )) return;
        await this._applySchedules([{
            postlog_id: row.id, schedule_id: alt.id,
            source: "manual", confirmed_override: true, replace_existing: replacing,
        }]);
    }

    async attachManual(row) {
        const reference = this.state.manualSchedule.trim();
        if (!reference) {
            this.notification.add("Enter a schedule name or Odoo ID.", { type: "warning" });
            return;
        }
        const replacing = row.status === "matched";
        if (!window.confirm(`${replacing ? "Replace the current" : "Attach this"} schedule using a manual override?`)) return;
        await this._applySchedules([{
            postlog_id: row.id, schedule_id: false, schedule_ref: reference,
            source: "manual", confirmed_override: true, replace_existing: replacing,
        }]);
    }

    /** Re-check from inside the drawer, keeping your place.
     *
     *  The rhythm this supports: several rows share one bad Schedule, you fix
     *  the Schedule in another tab, come back and want them gone so the next
     *  arrow lands on a genuinely different problem - not another row blocked
     *  by the thing you just fixed.
     *
     *  If the open row itself gets attached it drops out of the filtered list,
     *  and whatever slides into its index is the next thing needing review, so
     *  holding the index is exactly the right place to be.
     */
    async onDrawerRefresh() {
        const openId = this.state.drawerRow?.id;
        // Remember where this row sat before the list changes under us; the
        // arrows step from here once the row itself has dropped out.
        this.state.drawerAnchor = Math.max(this.drawerIndex, 0);
        await this.onRefresh();
        // Deliberately NOT rows[index]: the drawer follows the row you chose,
        // not a position in a list that just changed. If your fix worked, the
        // row is now Matched and you get to see that - swapping in a different
        // row would hide the one answer you pressed the button for.
        const fresh = openId
            ? await this.orm.call("mv.spot_data", "fuzzy_match_row", [openId])
            : false;
        if (fresh) {
            this.state.drawerRow = fresh;
        } else {
            this.closeDrawer();
        }
    }

    /** Where the open row sits in the loaded page, or -1 if it is not there. */
    get drawerIndex() {
        if (!this.state.drawerRow) {
            return -1;
        }
        return this.state.rows.findIndex((row) => row.id === this.state.drawerRow.id);
    }

    /** "3 of 12" - the page, not the whole result set, since that is what the
     *  arrows can actually reach. */
    get drawerPosition() {
        const index = this.drawerIndex;
        if (index < 0) {
            // No longer in this list - say so rather than showing a position
            // that belongs to some other row now.
            return this.state.drawerRow ? "not in view" : "";
        }
        return `${index + 1} of ${this.state.rows.length}`;
    }

    /** True when the open row has left the filtered list - it was attached by a
     *  Refresh and the tab no longer includes it. The arrows then step from the
     *  anchor, i.e. the slot it used to occupy. */
    get drawerDetached() {
        return !!this.state.drawerRow && this.drawerIndex < 0;
    }

    get hasPrevRow() {
        return this.drawerDetached
            ? this.state.drawerAnchor > 0
            : this.drawerIndex > 0;
    }

    get hasNextRow() {
        if (this.drawerDetached) {
            // rows[anchor] is whatever slid into this row's place: the next
            // thing needing review.
            return this.state.drawerAnchor < this.state.rows.length;
        }
        const index = this.drawerIndex;
        return index >= 0 && index < this.state.rows.length - 1;
    }

    /** Step to the neighbouring row without closing the drawer. Bounded by the
     *  loaded page: paging from inside the drawer would move the table under
     *  the operator, which is more surprising than stopping at the edge. */
    stepDrawer(delta) {
        const from = this.drawerDetached
            ? this.state.drawerAnchor - (delta > 0 ? 1 : 0)
            : this.drawerIndex;
        const next = this.state.rows[from + delta];
        if (next) {
            this.openDrawer(next);
        }
    }

    openDrawer(row) {
        this.state.drawerRow = row;
        this.state.drawerAnchor = Math.max(this.state.rows.indexOf(row), 0);
        this.state.manualSchedule = "";
    }
    closeDrawer() { this.state.drawerRow = false; this.state.manualSchedule = ""; }

    async onExport() {
        if (!this._filtersAreValid()) return;
        const f = this.state.filters;
        this.state.exporting = true;
        try {
            const result = await this.orm.call("mv.spot_data", "fuzzy_workbench_export_csv", [
                f.programId || false, f.weekStart || false, this.state.activeTab,
                this.state.searchTerm, this.state.airDate || false, this.state.issueFilter,
                this.state.sortBy, f.importJobId || false, this.state.sortDirection,
            ]);
            const blob = new Blob(["\ufeff", result.content || ""], { type: "text/csv;charset=utf-8" });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url; link.download = result.filename || "PostlogWorkbench.csv";
            document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url);
            this.notification.add(`${result.count || 0} row(s) exported.`, { type: "success" });
        } finally { this.state.exporting = false; }
    }

    async previousPage() {
        if (this.state.offset <= 0) return;
        this.state.offset = Math.max(this.state.offset - this.state.pageSize, 0);
        await this._loadResults();
    }
    async nextPage() {
        if (this.state.offset + this.state.pageSize >= this.state.total) return;
        this.state.offset += this.state.pageSize;
        await this._loadResults();
    }

    async onSort(column) {
        if (this.state.querying || this.state.mutating) return;
        if (this.state.sortBy === column) {
            this.state.sortDirection = this.state.sortDirection === "asc" ? "desc" : "asc";
        } else {
            this.state.sortBy = column;
            this.state.sortDirection = "asc";
        }
        this.state.offset = 0;
        this._resetSelection();
        this.state.drawerRow = false;
        await this._loadResults();
    }

    sortAria(column) {
        if (this.state.sortBy !== column) return "none";
        return this.state.sortDirection === "desc" ? "descending" : "ascending";
    }

    sortIcon(column) {
        if (this.state.sortBy !== column) return "fa fa-sort mv-fuzzy__sort-icon";
        const direction = this.state.sortDirection === "desc" ? "down" : "up";
        return `fa fa-sort-${direction} mv-fuzzy__sort-icon is-active`;
    }

    /** The ranked candidates for the drawer, suggestion first, normalized to one
     *  shape so the table renders in a single loop. The suggestion's per-field
     *  flags live on the row while a runner-up carries its own, which is the only
     *  reason this mapping exists. */
    candidates() {
        const row = this.state.drawerRow;
        if (!row || !row.suggested) {
            return [];
        }
        const shape = (schedule, flags, extra) => ({
            schedule,
            day_mismatch: flags.day_mismatch,
            time_mismatch: flags.time_mismatch,
            rate_mismatch: flags.rate_mismatch,
            length_mismatch: flags.length_mismatch,
            time_distance: flags.time_distance,
            exact_time_match: flags.exact_time_match,
            ...extra,
        });
        return [
            shape(row.suggested, row, {
                suggested: true,
                attachable: row.suggestion_attachable,
                alt: null,
            }),
            ...(row.alternatives || []).map((alt) =>
                shape(alt, alt, {
                    suggested: false,
                    attachable: alt.attachable,
                    alt,
                })
            ),
        ];
    }

    /** Candidate rate minus the spot's rate, signed. "" when they agree, so the
     *  delta only ever appears on a row that actually differs. */
    rateDelta(schedule) {
        const spot = Number(this.state.drawerRow?.rate ?? 0);
        const other = Number(schedule?.rate ?? 0);
        const diff = other - spot;
        if (!Number.isFinite(diff) || Math.abs(diff) < 0.005) {
            return "";
        }
        return `${diff > 0 ? "+" : "-"}$${this.formatRate(Math.abs(diff))}`;
    }

    /** Every check this candidate fails, counted the same four ways the ranking
     *  counts them, so the column explains the order instead of contradicting it.
     *  A green tick therefore means "nothing differs", never "the time is fine".
     *
     *  Says "outside rotation" rather than early/late on purpose: rotations may
     *  cross midnight, so a direction would sometimes be a lie. */
    differenceSummary(candidate) {
        const parts = [];
        if (candidate.day_mismatch) {
            // Name the day the spot aired: the operator's next question after
            // "wrong day" was always "wrong how?".
            const day = this.spotDayName();
            parts.push(day ? `Day Not Allowed - ${day}` : "Day Not Allowed");
        }
        if (!candidate.exact_time_match) {
            const distance = candidate.time_distance;
            const airTime = this.formatAirTime(this.state.drawerRow?.air_time);
            const howFar =
                distance === null || distance === undefined || distance === false
                    ? "outside rotation"
                    : `${distance} min outside rotation`;
            // Name the airtime that missed, the same way the day difference
            // names the day that was not allowed.
            parts.push(airTime ? `${howFar} - ${airTime}` : howFar);
        }
        if (candidate.rate_mismatch) {
            const delta = this.rateDelta(candidate.schedule);
            parts.push(delta ? `Rate ${delta}` : "Rate differs");
        }
        if (candidate.length_mismatch) {
            parts.push(`Length ${candidate.schedule.length}`);
        }
        return {
            count: parts.length,
            label: parts.length
                ? `${parts.length} difference${parts.length === 1 ? "" : "s"}`
                : "Exact match",
            // One per line. Joined on a middot they read as a single run-on
            // sentence once there is more than one.
            parts,
        };
    }

    /** "2026-08-08" -> "08/08/2026 \u00b7 Saturday".
     *  Built from the date parts rather than new Date(iso), which parses as UTC
     *  midnight and lands on the previous day west of Greenwich. */
    formatAirDate(value) {
        const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
        if (!m) {
            return value || "\u2014";
        }
        const [, y, mo, d] = m;
        const dayName = this.weekdayName(value);
        return `${mo}/${d}/${y}${dayName ? `\u00a0\u00b7\u00a0${dayName}` : ""}`;
    }

    /** Full weekday for an ISO date, e.g. "Saturday". Built from the date parts,
     *  not new Date(iso), which parses as UTC midnight and lands on the previous
     *  day west of Greenwich. "" when the value cannot be parsed. */
    weekdayName(value) {
        const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
        if (!m) {
            return "";
        }
        const local = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
        return Number.isNaN(local.getTime())
            ? ""
            : local.toLocaleDateString(undefined, { weekday: "long" });
    }

    /** The weekday the spot aired. Falls back to the server's abbreviation
     *  ("Sat") if the air date is missing or unparseable. */
    spotDayName() {
        const row = this.state.drawerRow;
        return this.weekdayName(row?.air_date) || row?.day || "";
    }

    /** "05:10:15" -> "05:10:15 AM"; "17:10:15" -> "05:10:15 PM". */
    formatAirTime(value) {
        const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(String(value || ""));
        if (!m) {
            return value || "\u2014";
        }
        const raw = Number(m[1]);
        const suffix = raw < 12 ? "AM" : "PM";
        const hour = raw % 12 || 12;
        return `${String(hour).padStart(2, "0")}:${m[2]}:${m[3] || "00"} ${suffix}`;
    }

    /** "Mon, Tue, Wed, Thu, Fri, Sat, Sun" -> "Mon\u2013Sun" when contiguous.
     *  Keeps the ranked table's Time & Days column narrow. Falls back to the
     *  original string for gapped sets like Mon, Wed, Fri. */
    condenseDays(value) {
        const order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        const parts = String(value || "").split(",").map((d) => d.trim()).filter(Boolean);
        if (parts.length < 3) {
            return parts.join(", ") || "\u2014";
        }
        const idx = parts.map((d) => order.indexOf(d.slice(0, 3)));
        if (idx.some((i) => i < 0)) {
            return parts.join(", ");
        }
        const sorted = [...idx].sort((a, b) => a - b);
        const contiguous = sorted.every((v, i) => i === 0 || v === sorted[i - 1] + 1);
        return contiguous
            ? `${order[sorted[0]]}\u2013${order[sorted[sorted.length - 1]]}`
            : parts.join(", ");
    }

    formatRate(value) {
        const number = Number(value || 0);
        return Number.isFinite(number) ? number.toLocaleString(undefined, {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        }) : "";
    }
    /** Two badges for two stored states. Not `--${row.status}`: that emitted a
     *  third, red, No Suggestion badge for a split the Info column now makes. */
    statusBadge(row) {
        if (row.status === "matched") {
            return "mv-fuzzy__status mv-fuzzy__status--matched";
        }
        if (row.status === "removed") {
            return "mv-fuzzy__status mv-fuzzy__status--removed";
        }
        return "mv-fuzzy__status mv-postlog-status--unmatched";
    }
    tabTitle() {
        return {
            all: "All",
            matched: "Matched",
            unmatched: "Unmatched",
            suggestions: "Suggestions",
            no_suggestion: "No Suggestion",
            removed: "Removed",
        }[this.state.activeTab] || "All";
    }

    async openPostlog(row) {
        await this.action.doAction({
            type: "ir.actions.act_window", name: row.name, res_model: "mv.spot_data",
            res_id: row.id, views: [[false, "form"]], target: "current",
        });
    }
    scheduleOpenUrl(schedule) {
        if (!schedule?.id) return "#";
        return `/odoo/mv.schedules/${schedule.id}`;
    }
}

registry.category("actions").add("mv_postlog_matching", MvPostlogMatching);
