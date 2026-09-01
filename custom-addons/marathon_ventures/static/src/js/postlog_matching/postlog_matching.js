/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class MvPostlogMatching extends Component {
    static template = "marathon_ventures.MvPostlogMatching";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.requestId = 0;
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
            counts: { all: 0, matched: 0, unmatched: 0, suggestions: 0, no_suggestion: 0 },
            searchTerm: "",
            airDate: "",
            issueFilter: "",
            refreshing: false,
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
    /** Open the Postlog upload wizard without leaving the workbench. Reloads on
     *  close so a completed import shows up without a manual refresh. */
    async onImport() {
        await this.action.doAction(
            "marathon_ventures.action_open_postlog_upload_wizard",
            { onClose: () => this._loadResults() },
        );
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

    openDrawer(row) {
        this.state.drawerRow = row;
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
    statusBadge(row) { return `mv-fuzzy__status mv-fuzzy__status--${row.status}`; }
    tabTitle() {
        return {
            all: "All",
            matched: "Matched",
            unmatched: "Unmatched",
            suggestions: "Suggestions",
            no_suggestion: "No Suggestion",
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
