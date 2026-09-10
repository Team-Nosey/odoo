/** @odoo-module **/
/*  Hiatus Deals - OWL page (originally ported from the Salesforce
 *  `hiatusDealComponent` LWC, since restructured).
 *
 *  FILTER FLOW
 *  -----------
 *  Date is the gate. Nothing else is usable until at least one date is
 *  picked; once one is, the Program / Advertiser / Agency lists are
 *  fetched from the deals that actually fall in that range, so an option
 *  that no in-range deal carries is never offered.
 *
 *      Select Date(s) -> options load -> multi-select filters -> Search
 *
 *  All three list filters are the SAME component (HiatusMultiSelect), so
 *  their markup, keyboard behaviour, filter box, select-all/clear and
 *  chip summary are identical by construction rather than by copy-paste.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillUnmount } from "@odoo/owl";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const OPTIONS_DEBOUNCE_MS = 350;

// =========================================================================
// HiatusMultiSelect - one component, three filters.
// =========================================================================
export class HiatusMultiSelect extends Component {
    static template = "marathon_ventures.HiatusMultiSelect";
    static props = {
        label: { type: String },
        placeholder: { type: String },
        options: { type: Array },            // [{value, label}]
        selected: { type: Array },           // [value, ...]
        disabled: { type: Boolean, optional: true },
        emptyHint: { type: String, optional: true },
        onChange: { type: Function },        // (nextSelectedArray) => void
    };

    setup() {
        this.ui = useState({ open: false, term: "" });
    }

    get filtered() {
        const term = (this.ui.term || "").toLowerCase().trim();
        if (!term) return this.props.options;
        return this.props.options.filter(
            (o) => (o.label || "").toLowerCase().includes(term),
        );
    }

    get summary() {
        const n = this.props.selected.length;
        const total = this.props.options.length;
        if (!total) return this.props.emptyHint || "No options";
        if (n === 0) return this.props.placeholder;
        if (n === 1) {
            const hit = this.props.options.find(
                (o) => o.value === this.props.selected[0],
            );
            return hit ? hit.label : "1 selected";
        }
        return `${n} of ${total} selected`;
    }

    get hasSelection() {
        return this.props.selected.length > 0;
    }

    isChecked(value) {
        return this.props.selected.includes(value);
    }

    toggle() {
        if (this.props.disabled) return;
        this.ui.open = !this.ui.open;
        if (!this.ui.open) this.ui.term = "";
    }

    close() {
        this.ui.open = false;
        this.ui.term = "";
    }

    onTermInput(ev) {
        this.ui.term = ev.target.value;
    }

    onToggleOption(value) {
        const next = this.props.selected.includes(value)
            ? this.props.selected.filter((v) => v !== value)
            : [...this.props.selected, value];
        this.props.onChange(next);
    }

    /** Select-all applies to what the filter box currently shows, which
     *  is what the user can actually see - not the whole hidden list. */
    onSelectAllVisible(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const visible = this.filtered.map((o) => o.value);
        const merged = [...new Set([...this.props.selected, ...visible])];
        this.props.onChange(merged);
    }

    onClear(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.props.onChange([]);
    }

    onKeydown(ev) {
        if (ev.key === "Escape") this.close();
    }
}

// =========================================================================
// MvHiatusDeals - the page
// =========================================================================
export class MvHiatusDeals extends Component {
    static template = "marathon_ventures.MvHiatusDeals";
    static components = { HiatusMultiSelect };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const today = new Date();
        this.state = useState({
            loading: false,

            // ── Step 1: dates (the gate) ──────────────────────────
            selectedDates: [],
            viewYear: today.getFullYear(),
            viewMonth: today.getMonth(),
            datePickerOpen: false,

            // ── Step 2: options derived from those dates ─────────
            optionsLoading: false,
            optionsLoaded: false,
            optionsError: "",
            options: { programs: [], advertisers: [], agencies: [] },
            inRangeDealCount: 0,

            // ── Step 3: multi-select values ─────────────────────
            selectedPrograms: [],
            selectedAdvertisers: [],
            selectedAgencies: [],

            // ── Results ─────────────────────────────────────────
            rows: [],
            hasSearched: false,
        });

        this._timers = {};
        this._optionsToken = 0;

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
        return (error.data && error.data.message) || error.message || String(error);
    }

    _notify(message, type) {
        this.notification.add(message, { type });
    }

    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    }

    // ── Step 1: dates ─────────────────────────────────────────────────
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

    get hasDates() {
        return this.state.selectedDates.length > 0;
    }

    get datePickerLabel() {
        const n = this.state.selectedDates.length;
        if (n === 0) return "Select date(s) to begin";
        if (n === 1) {
            const [y, m, d] = [...this.state.selectedDates][0].split("-");
            return `${m}/${d}/${y}`;
        }
        return `${n} dates selected`;
    }

    get selectedDatePills() {
        return [...this.state.selectedDates].sort().map((value) => {
            const [y, m, d] = value.split("-");
            return { value, label: `${m}/${d}/${y}` };
        });
    }

    onDateClick(ev) {
        const dateStr = ev.currentTarget.dataset.date;
        if (!dateStr) return;
        this.state.selectedDates = this.state.selectedDates.includes(dateStr)
            ? this.state.selectedDates.filter((d) => d !== dateStr)
            : [...this.state.selectedDates, dateStr].sort();
        this._onDatesChanged();
    }

    removeDatePill(value) {
        this.state.selectedDates = this.state.selectedDates.filter(
            (d) => d !== value,
        );
        this._onDatesChanged();
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
        this._onDatesChanged();
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

    /**
     * Dates changed -> the downstream filters are stale by definition.
     * Reset them and reload the option lists (debounced, so clicking
     * several dates in a row is one round trip).
     */
    _onDatesChanged() {
        this.state.selectedPrograms = [];
        this.state.selectedAdvertisers = [];
        this.state.selectedAgencies = [];
        this.state.rows = [];
        this.state.hasSearched = false;
        this.state.optionsError = "";

        if (!this.hasDates) {
            this.state.options = { programs: [], advertisers: [], agencies: [] };
            this.state.optionsLoaded = false;
            this.state.inRangeDealCount = 0;
            this._optionsToken++;          // cancel any in-flight load
            return;
        }
        this._debounce("options", () => this.loadFilterOptions(), OPTIONS_DEBOUNCE_MS);
    }

    // ── Step 2: options ───────────────────────────────────────────────
    async loadFilterOptions() {
        const token = ++this._optionsToken;
        this.state.optionsLoading = true;
        this.state.optionsError = "";
        try {
            const res = await this.orm.call(
                "mv.deal", "hiatus_get_filter_options", [this.selectedDatesCsv],
            );
            if (token !== this._optionsToken) return;   // a newer load won
            this.state.options = {
                programs: res.programs || [],
                advertisers: res.advertisers || [],
                agencies: res.agencies || [],
            };
            this.state.inRangeDealCount = res.deal_count || 0;
            this.state.optionsLoaded = true;
        } catch (e) {
            if (token !== this._optionsToken) return;
            this.state.options = { programs: [], advertisers: [], agencies: [] };
            this.state.optionsLoaded = false;
            this.state.optionsError = this._err(e);
        } finally {
            if (token === this._optionsToken) this.state.optionsLoading = false;
        }
    }

    get filtersDisabled() {
        return !this.hasDates || this.state.optionsLoading;
    }

    get optionsSummary() {
        if (!this.hasDates) return "Pick date(s) first";
        if (this.state.optionsLoading) return "Loading filters…";
        if (this.state.optionsError) return this.state.optionsError;
        if (!this.state.optionsLoaded) return "";
        const o = this.state.options;
        return `${this.state.inRangeDealCount} deal(s) in range · ` +
               `${o.programs.length} program(s) · ` +
               `${o.advertisers.length} advertiser(s) · ` +
               `${o.agencies.length} agency/agencies`;
    }

    // Bound handlers for the three multi-selects.
    onProgramsChange(next) { this.state.selectedPrograms = next; }
    onAdvertisersChange(next) { this.state.selectedAdvertisers = next; }
    onAgenciesChange(next) { this.state.selectedAgencies = next; }

    // ── Step 3: search ────────────────────────────────────────────────
    get canSearch() {
        return this.hasDates && !this.state.loading && !this.state.optionsLoading;
    }

    get searchBlockedReason() {
        if (!this.hasDates) return "Select at least one date to enable Search.";
        if (this.state.optionsLoading) return "Loading filter options…";
        return "";
    }

    async onSearch() {
        if (!this.hasDates) {
            this._notify(
                "Select at least one date on the calendar before searching.",
                "warning",
            );
            return;
        }
        await this.runSearch();
    }

    async runSearch() {
        this.state.loading = true;
        try {
            const res = await this.orm.call("mv.deal", "hiatus_search_deals", [
                this.selectedDatesCsv,
                this.state.selectedPrograms,
                this.state.selectedAdvertisers,
                this.state.selectedAgencies,
            ]);
            this.state.rows = (res || []).map((r) => ({ ...r, selected: false }));
            this.state.hasSearched = true;
        } catch (e) {
            this.state.rows = [];
            this._notify(`Search failed: ${this._err(e)}`, "danger");
        } finally {
            this.state.loading = false;
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

    onRowSelect(row, ev) {
        row.selected = ev.target.checked;
    }

    onSelectAll(ev) {
        const checked = ev.target.checked;
        for (const row of this.state.rows) row.selected = checked;
    }

    async onRemoveRow(row) {
        this.state.loading = true;
        try {
            await this.orm.call("mv.deal", "hiatus_remove_from_results", [row.id]);
            this.state.rows = this._applyGroupHeaders(
                this.state.rows.filter((r) => r.id !== row.id),
            );
        } catch (e) {
            this._notify(`Unable to remove deal: ${this._err(e)}`, "danger");
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
        if (!this.hasDates) {
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
            this._notify(`Unable to apply hiatus dates: ${this._err(e)}`, "danger");
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
            this._notify(`Unable to clear hiatus dates: ${this._err(e)}`, "danger");
        } finally {
            this.state.loading = false;
        }
    }
}

registry.category("actions").add("mv_hiatus_deals", MvHiatusDeals);
