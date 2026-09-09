/** @odoo-module **/
/*  Hiatus Deals - OWL port of the Salesforce `hiatusDealComponent` LWC.
 *
 *  LWC -> OWL mapping
 *  ------------------
 *    @track field              -> useState() slice
 *    getter                    -> getter (unchanged concept)
 *    @salesforce/apex/... call -> this.orm.call("mv.deal", "<method>", [...])
 *    ShowToastEvent            -> notification service
 *    lightning-spinner         -> state.loading + a spinner div
 *    lightning-card            -> plain markup + SCSS
 *    slds-* classes            -> Bootstrap / o_* / hd-* classes
 *
 *  Behaviour preserved from the LWC:
 *    - Program combobox: type-ahead over a client-side cached list, keyboard
 *      nav (Up/Down/Enter/Escape), "-- All Programs --" sentinel, clear
 *      button, truncation note past MAX_VISIBLE_OPTIONS, and free-text
 *      resolution on Search (unique match wins, ambiguous match blocks).
 *    - Advertiser combobox: server-side debounced search, keyboard nav,
 *      exact-vs-free-text distinction (advertiserExact).
 *    - Calendar: multi-select day toggles, month paging, dropdown with
 *      backdrop, Clear / Done, debounced agency refresh on change.
 *    - Agencies: native multi-select, client-side filter box, hidden
 *      selections survive filtering, stale-request guard via a token.
 *    - Results: group headers, green/red row shading, select-all,
 *      per-row remove, bulk hiatus / clear-hiatus with validation, and a
 *      re-search after each mutation.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";

const ALL_PROGRAMS_LABEL = "-- All Programs --";
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const SEARCH_DEBOUNCE_MS = 300;
const AGENCY_REFRESH_DEBOUNCE_MS = 350;
const MAX_VISIBLE_OPTIONS = 100;

export class MvHiatusDeals extends Component {
    static template = "marathon_ventures.MvHiatusDeals";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const today = new Date();
        this.state = useState({
            loading: false,

            // Program combobox
            programOptions: [],
            programSearchTerm: "",
            selectedProgramId: "",
            programOpen: false,
            programFilterActive: false,
            programActiveIndex: -1,

            // Advertiser combobox
            advertiserOptions: [],
            advertiserSearchTerm: "",
            selectedAdvertiserName: "",
            advertiserExact: false,
            advertiserOpen: false,
            advertiserActiveIndex: -1,

            // Calendar
            selectedDates: [],
            viewYear: today.getFullYear(),
            viewMonth: today.getMonth(),
            datePickerOpen: false,

            // Agencies
            agencyOptions: [],
            selectedAgencies: [],
            agencySearchTerm: "",
            agencyLoading: false,
            agencyMessage: "",

            // Results
            rows: [],
            hasSearched: false,
        });

        this._timers = {};
        this._agencyToken = 0;

        onWillStart(async () => {
            await Promise.all([this.loadPrograms(), this.loadAdvertisers("")]);
        });

        onWillUnmount(() => {
            for (const key of Object.keys(this._timers)) {
                window.clearTimeout(this._timers[key]);
            }
        });
    }

    // ── helpers ───────────────────────────────────────────────────────
    _debounce(key, fn, delay) {
        window.clearTimeout(this._timers[key]);
        this._timers[key] = window.setTimeout(fn, delay);
    }

    _err(error) {
        if (!error) return "Unknown error";
        if (typeof error === "string") return error;
        return (
            (error.data && error.data.message) || error.message || String(error)
        );
    }

    _notify(message, type) {
        this.notification.add(message, { type });
    }

    _showError(title, error) {
        this._notify(`${title}: ${this._err(error)}`, "danger");
    }

    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    }

    // ── option loading ────────────────────────────────────────────────
    async loadPrograms() {
        try {
            const res = await this.orm.call(
                "mv.deal", "hiatus_get_program_options", [],
            );
            this.state.programOptions = (res || []).map((o) => ({
                label: o.label, value: o.value,
            }));
        } catch (e) {
            this._showError("Unable to load programs", e);
        }
    }

    async loadAdvertisers(searchTerm) {
        try {
            const res = await this.orm.call(
                "mv.deal", "hiatus_get_advertiser_options", [searchTerm || ""],
            );
            this.state.advertiserOptions = (res || []).map((o) => ({
                label: o.label, value: o.value, recordId: o.recordId,
            }));
            this.state.advertiserActiveIndex = -1;
        } catch (e) {
            this._showError("Unable to load advertisers", e);
        }
    }

    // ── Program combobox ──────────────────────────────────────────────
    get programMatches() {
        const term = this.state.programFilterActive
            ? (this.state.programSearchTerm || "").toLowerCase().trim()
            : "";
        if (!term) return this.state.programOptions;
        return this.state.programOptions.filter(
            (o) => (o.label || "").toLowerCase().includes(term),
        );
    }

    get programListItems() {
        const items = [{ label: ALL_PROGRAMS_LABEL, value: "" }].concat(
            this.programMatches.slice(0, MAX_VISIBLE_OPTIONS),
        );
        return items.map((o, index) => ({
            key: o.value || "__all_programs__",
            label: o.label,
            value: o.value,
            active: index === this.state.programActiveIndex,
        }));
    }

    get noProgramMatches() {
        return (
            this.programListItems.length <= 1 &&
            this.state.programOptions.length > 0
        );
    }

    get showProgramTruncatedNote() {
        return this.programMatches.length > MAX_VISIBLE_OPTIONS;
    }

    get programTruncatedNote() {
        return `Showing the first ${MAX_VISIBLE_OPTIONS} of ${this.programMatches.length} programs — keep typing to narrow the list.`;
    }

    get hasProgramSelection() {
        return !!this.state.selectedProgramId || !!this.state.programSearchTerm;
    }

    onProgramFocus() {
        this.state.programFilterActive = false;
        this.state.programActiveIndex = -1;
        this.state.programOpen = true;
    }

    onProgramInput(ev) {
        this.state.programFilterActive = true;
        this.state.programSearchTerm = ev.target.value;
        this.state.selectedProgramId = "";
        this.state.programActiveIndex = -1;
        this.state.programOpen = true;
    }

    onProgramKeyDown(ev) {
        const items = this.programListItems;
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.programOpen = true;
            this.state.programActiveIndex = Math.min(
                this.state.programActiveIndex + 1, items.length - 1,
            );
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.programActiveIndex = Math.max(
                this.state.programActiveIndex - 1, 0,
            );
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            const item = items[this.state.programActiveIndex];
            if (item) this.selectProgram(item.value, item.label);
            else this.state.programOpen = false;
        } else if (ev.key === "Escape") {
            this.state.programOpen = false;
        }
    }

    selectProgram(value, label) {
        const changed = this.state.selectedProgramId !== (value || "");
        this.state.selectedProgramId = value || "";
        this.state.programSearchTerm = value ? label : "";
        this.state.programFilterActive = false;
        this.state.programActiveIndex = -1;
        this.state.programOpen = false;
        if (changed) this.scheduleAgencyRefresh();
    }

    onProgramBlur() {
        // Delay so a mousedown on an option is processed first.
        this._debounce("programBlur", () => {
            this.state.programOpen = false;
        }, 0);
    }

    onClearProgram(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.selectProgram("", ALL_PROGRAMS_LABEL);
    }

    // ── Advertiser combobox ───────────────────────────────────────────
    get advertiserListItems() {
        return this.state.advertiserOptions
            .slice(0, MAX_VISIBLE_OPTIONS)
            .map((o, index) => ({
                key: String(o.recordId || o.value),
                label: o.label,
                value: o.value,
                active: index === this.state.advertiserActiveIndex,
            }));
    }

    get noAdvertiserMatches() {
        return this.advertiserListItems.length === 0;
    }

    get hasAdvertiserText() {
        return !!this.state.advertiserSearchTerm;
    }

    get advertiserSearchText() {
        return this.state.advertiserExact
            ? this.state.selectedAdvertiserName
            : (this.state.advertiserSearchTerm || "").trim();
    }

    onAdvertiserFocus() {
        this.state.advertiserActiveIndex = -1;
        this.state.advertiserOpen = true;
    }

    onAdvertiserInput(ev) {
        const term = ev.target.value;
        this.state.advertiserSearchTerm = term;
        // Typing means the user is no longer bound to a picked advertiser.
        this.state.selectedAdvertiserName = "";
        this.state.advertiserExact = false;
        this.state.advertiserActiveIndex = -1;
        this.state.advertiserOpen = true;
        this._debounce(
            "advertiser", () => this.loadAdvertisers(term), SEARCH_DEBOUNCE_MS,
        );
    }

    onAdvertiserKeyDown(ev) {
        const items = this.advertiserListItems;
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.advertiserOpen = true;
            this.state.advertiserActiveIndex = Math.min(
                this.state.advertiserActiveIndex + 1, items.length - 1,
            );
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.advertiserActiveIndex = Math.max(
                this.state.advertiserActiveIndex - 1, 0,
            );
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            const item = items[this.state.advertiserActiveIndex];
            if (item) this.selectAdvertiser(item.value, item.label);
            else this.state.advertiserOpen = false;
        } else if (ev.key === "Escape") {
            this.state.advertiserOpen = false;
        }
    }

    selectAdvertiser(value, label) {
        this.state.selectedAdvertiserName = value;
        this.state.advertiserSearchTerm = label;
        this.state.advertiserExact = true;
        this.state.advertiserActiveIndex = -1;
        this.state.advertiserOpen = false;
    }

    onAdvertiserBlur() {
        this._debounce("advertiserBlur", () => {
            this.state.advertiserOpen = false;
        }, 0);
    }

    onClearAdvertiser(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.advertiserSearchTerm = "";
        this.state.selectedAdvertiserName = "";
        this.state.advertiserExact = false;
        this.state.advertiserOpen = false;
        this.loadAdvertisers("");
    }

    // ── Calendar ──────────────────────────────────────────────────────
    get weekdayLabels() {
        return WEEKDAYS;
    }

    get monthLabel() {
        return `${MONTHS[this.state.viewMonth]} ${this.state.viewYear}`;
    }

    get calendarWeeks() {
        const cursor = new Date(this.state.viewYear, this.state.viewMonth, 1);
        cursor.setDate(1 - cursor.getDay());
        const weeks = [];
        for (let w = 0; w < 6; w++) {
            const days = [];
            for (let d = 0; d < 7; d++) {
                const dateStr = this.formatDate(cursor);
                const inMonth = cursor.getMonth() === this.state.viewMonth;
                const isSelected =
                    inMonth && this.state.selectedDates.includes(dateStr);
                let cssClass = "hd-cal-cell";
                cssClass += inMonth ? " hd-in-month" : " hd-out-month";
                if (isSelected) cssClass += " hd-selected";
                days.push({
                    key: dateStr,
                    label: cursor.getDate(),
                    dateStr: inMonth ? dateStr : "",
                    cssClass,
                });
                cursor.setDate(cursor.getDate() + 1);
            }
            weeks.push({ key: `week-${w}`, days });
        }
        return weeks;
    }

    get selectedDatesCsv() {
        return [...this.state.selectedDates].sort().join(",");
    }

    get hasSelectedDates() {
        return this.state.selectedDates.length > 0;
    }

    get datePickerLabel() {
        const n = this.state.selectedDates.length;
        if (n === 0) return "No dates selected";
        if (n === 1) {
            const [y, m, d] = [...this.state.selectedDates][0].split("-");
            return `${m}/${d}/${y}`;
        }
        return `${n} dates selected`;
    }

    onDateClick(ev) {
        const dateStr = ev.currentTarget.dataset.date;
        if (!dateStr) return;
        if (this.state.selectedDates.includes(dateStr)) {
            this.state.selectedDates = this.state.selectedDates.filter(
                (d) => d !== dateStr,
            );
        } else {
            this.state.selectedDates = [
                ...this.state.selectedDates, dateStr,
            ].sort();
        }
        this.scheduleAgencyRefresh();
    }

    onPreviousMonth() {
        const d = new Date(this.state.viewYear, this.state.viewMonth - 1, 1);
        this.state.viewYear = d.getFullYear();
        this.state.viewMonth = d.getMonth();
    }

    onNextMonth() {
        const d = new Date(this.state.viewYear, this.state.viewMonth + 1, 1);
        this.state.viewYear = d.getFullYear();
        this.state.viewMonth = d.getMonth();
    }

    onClearDates() {
        if (!this.state.selectedDates.length) return;
        this.state.selectedDates = [];
        this.scheduleAgencyRefresh();
    }

    toggleDatePicker() {
        this.state.datePickerOpen = !this.state.datePickerOpen;
    }

    closeDatePicker() {
        this.state.datePickerOpen = false;
    }

    onDatePickerKeydown(ev) {
        if (ev.key === "Escape") this.closeDatePicker();
    }

    // ── Agencies ──────────────────────────────────────────────────────
    get hasAgencies() {
        return this.state.agencyOptions.length > 0;
    }

    get hasSelectedAgencies() {
        return this.state.selectedAgencies.length > 0;
    }

    get filteredAgencyOptions() {
        const term = (this.state.agencySearchTerm || "").toLowerCase().trim();
        if (!term) return this.state.agencyOptions;
        return this.state.agencyOptions.filter(
            (o) => (o.label || "").toLowerCase().includes(term),
        );
    }

    get agencyHelpText() {
        const selected = this.state.selectedAgencies.length;
        const shown = this.filteredAgencyOptions.length;
        const total = this.state.agencyOptions.length;
        const scope =
            shown === total ? `${total} agencies` : `${shown} of ${total} agencies`;
        return selected
            ? `${scope} · ${selected} selected · hold Ctrl / Cmd to pick more`
            : `${scope} · hold Ctrl / Cmd to select more than one`;
    }

    get agencyEmptyText() {
        if (this.state.agencyLoading) return "Loading agencies…";
        if (this.state.agencyMessage) return this.state.agencyMessage;
        return "Choose a program and/or date(s) and the matching agencies will load here.";
    }

    get agencyStatusText() {
        if (this.state.agencyLoading) return "Loading…";
        if (this.hasAgencies) {
            const selected = this.state.selectedAgencies.length;
            const total = this.state.agencyOptions.length;
            return selected
                ? `${total} agencies · ${selected} selected`
                : `${total} agencies`;
        }
        if (this.state.agencyMessage) return "No matches";
        return "Awaiting search";
    }

    onAgencyFilter(ev) {
        this.state.agencySearchTerm = ev.target.value;
    }

    onAgencyChange(ev) {
        // Selections hidden by the filter must survive a change to the
        // visible ones.
        const visible = new Set(this.filteredAgencyOptions.map((o) => o.value));
        const hidden = this.state.selectedAgencies.filter(
            (v) => !visible.has(v),
        );
        const picked = Array.from(ev.target.selectedOptions).map((o) => o.value);
        this.state.selectedAgencies = [...new Set([...hidden, ...picked])];
    }

    isAgencySelected(value) {
        return this.state.selectedAgencies.includes(value);
    }

    onClearAgencies(ev) {
        if (ev) ev.preventDefault();
        this.state.selectedAgencies = [];
    }

    /** Debounced so clicking several dates in a row triggers one reload. */
    scheduleAgencyRefresh() {
        this._debounce(
            "agency", () => this.refreshAgencies(), AGENCY_REFRESH_DEBOUNCE_MS,
        );
    }

    async refreshAgencies() {
        if (!this.state.selectedDates.length && !this.state.selectedProgramId) {
            this.state.agencyOptions = [];
            this.state.selectedAgencies = [];
            this.state.agencySearchTerm = "";
            this.state.agencyMessage = "";
            return;
        }
        const token = ++this._agencyToken;
        this.state.agencyLoading = true;
        try {
            const res = await this.orm.call(
                "mv.deal", "hiatus_get_agency_options",
                [this.selectedDatesCsv, this.state.selectedProgramId || false],
            );
            if (token !== this._agencyToken) return;   // a newer request won
            const options = (res || []).map((o) => ({
                label: o.label, value: o.value,
            }));
            const valid = new Set(options.map((o) => o.value));
            this.state.agencyOptions = options;
            // Keep whatever the user had picked that still applies.
            this.state.selectedAgencies = this.state.selectedAgencies.filter(
                (v) => valid.has(v),
            );
            this.state.agencyMessage = options.length
                ? ""
                : "No agencies found for the selected program and date.";
        } catch (e) {
            if (token !== this._agencyToken) return;
            this.state.agencyOptions = [];
            this.state.selectedAgencies = [];
            this.state.agencyMessage = this._err(e);
        } finally {
            if (token === this._agencyToken) this.state.agencyLoading = false;
        }
    }

    // ── Results ───────────────────────────────────────────────────────
    get hasResults() {
        return this.state.rows.length > 0;
    }

    get resultsSummary() {
        if (!this.hasResults) return "";
        return `${this.state.rows.length} deal(s) · ${this.selectedDealIds.length} selected`;
    }

    get allRowsSelected() {
        return this.hasResults && this.state.rows.every((r) => r.selected);
    }

    get selectedDealIds() {
        return this.state.rows.filter((r) => r.selected).map((r) => r.id);
    }

    rowCellClass(row) {
        return row.hasSelectedDates
            ? "hd-cell hd-cell_hiatused"
            : "hd-cell hd-cell_open";
    }

    /**
     * The Program box accepts free text, but the search filters on a program
     * id. Resolve typed text to a single match, or tell the user to pick one
     * rather than silently searching every program.
     */
    resolveProgramSelection() {
        if (this.state.selectedProgramId) return true;
        const term = (this.state.programSearchTerm || "").trim().toLowerCase();
        if (!term || term === ALL_PROGRAMS_LABEL.toLowerCase()) {
            this.state.programSearchTerm = "";
            return true;
        }
        const opts = this.state.programOptions;
        const exact = opts.filter((o) => (o.label || "").toLowerCase() === term);
        const partial = opts.filter(
            (o) => (o.label || "").toLowerCase().includes(term),
        );
        const match =
            exact.length === 1 ? exact[0] : partial.length === 1 ? partial[0] : null;
        if (match) {
            this.selectProgram(match.value, match.label);
            return true;
        }
        this._notify(
            partial.length
                ? `"${this.state.programSearchTerm}" matches ${partial.length} programs. Pick one from the list, or clear the field to search all programs.`
                : `No program matches "${this.state.programSearchTerm}". Pick one from the list, or clear the field to search all programs.`,
            "danger",
        );
        return false;
    }

    async onSearch() {
        if (!this.resolveProgramSelection()) return;
        await this.runSearch();
    }

    async runSearch() {
        this.state.loading = true;
        try {
            const res = await this.orm.call("mv.deal", "hiatus_search_deals", [
                this.selectedDatesCsv,
                this.state.selectedProgramId || false,
                this.state.selectedAgencies,
                this.advertiserSearchText,
                this.state.advertiserExact,
            ]);
            this.state.rows = (res || []).map((r) => ({
                ...r, selected: false,
            }));
            this.state.hasSearched = true;
        } catch (e) {
            this.state.rows = [];
            this._showError("Search failed", e);
        } finally {
            this.state.loading = false;
        }
    }

    onRowSelect(row, ev) {
        row.selected = ev.target.checked;
    }

    onSelectAll(ev) {
        const checked = ev.target.checked;
        for (const row of this.state.rows) {
            row.selected = checked;
        }
    }

    async onRemoveRow(row) {
        this.state.loading = true;
        try {
            await this.orm.call(
                "mv.deal", "hiatus_remove_from_results", [row.id],
            );
            this.state.rows = this._applyGroupHeaders(
                this.state.rows.filter((r) => r.id !== row.id),
            );
        } catch (e) {
            this._showError("Unable to remove deal", e);
        } finally {
            this.state.loading = false;
        }
    }

    _applyGroupHeaders(rows) {
        let last = null;
        for (const r of rows) {
            r.showGroupHeader = r.groupKey !== last;
            last = r.groupKey;
        }
        return rows;
    }

    // ── Hiatus actions ────────────────────────────────────────────────
    _validateHiatusAction(actionLabel) {
        if (!this.state.selectedDates.length) {
            this._notify(
                `Select at least one date on the calendar before clicking "${actionLabel}".`,
                "danger",
            );
            return false;
        }
        if (!this.selectedDealIds.length) {
            this._notify("Check at least one deal in the results.", "danger");
            return false;
        }
        return true;
    }

    async onHiatusSelected() {
        if (!this._validateHiatusAction("Hiatus Selected Deals")) return;
        this.state.loading = true;
        try {
            const count = await this.orm.call("mv.deal", "hiatus_apply", [
                this.selectedDealIds, this.selectedDatesCsv,
            ]);
            this._notify(`Hiatus dates applied to ${count} deal(s).`, "success");
            await this.runSearch();
        } catch (e) {
            this._showError("Unable to apply hiatus dates", e);
        } finally {
            this.state.loading = false;
        }
    }

    async onClearHiatus() {
        if (!this._validateHiatusAction("Clear Hiatus Selected Deals")) return;
        this.state.loading = true;
        try {
            const count = await this.orm.call("mv.deal", "hiatus_clear", [
                this.selectedDealIds, this.selectedDatesCsv,
            ]);
            this._notify(`Hiatus dates cleared from ${count} deal(s).`, "success");
            await this.runSearch();
        } catch (e) {
            this._showError("Unable to clear hiatus dates", e);
        } finally {
            this.state.loading = false;
        }
    }
}

registry.category("actions").add("mv_hiatus_deals", MvHiatusDeals);
