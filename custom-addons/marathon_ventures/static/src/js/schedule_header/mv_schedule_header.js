/** @odoo-module **/

/*  Schedule form: header buttons beside the record name.
 *
 *  The Schedule form's <header> holds Save and Cancel/Uncancel Schedule.
 *  Odoo renders a <header> as a band across the top of the sheet, one row
 *  below the breadcrumb - so the form opened with the record name in the
 *  breadcrumb and a separate strip of buttons underneath it. Arianna's
 *  layout puts those buttons up on the breadcrumb row itself, next to the
 *  name and the cog, which is also where Odoo's own save indicator lives.
 *
 *  There is no view attribute for that: the breadcrumb row is built by the
 *  control panel, and its only openings are the cog menu and the save
 *  indicator. So the rendered button container is moved into it instead.
 *
 *  The move is re-applied after every render of the form rather than from a
 *  standing MutationObserver, so it is driven by Owl's own lifecycle: when
 *  Owl rebuilds the form (a different record, a reload, a status change that
 *  swaps Cancel for Uncancel) the fresh container is relocated in the same
 *  pass. Nothing here re-creates the buttons or duplicates their `invisible`
 *  conditions - the view arch stays the single definition, and Owl keeps
 *  patching the container it owns wherever it now sits.
 */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useEffect } from "@odoo/owl";

// Only this model. The Deal form shares the mv-deal-redesign styling and has
// a header of its own, which stays where it is.
const MODEL = "mv.schedules";
const RELOCATED = "mv-schedule-header-actions";

function relocateHeaderButtons(root) {
    if (!root) {
        return;
    }
    // The control panel is a sibling of the form, so reach for it from the
    // document: `root` is the form view only.
    const breadcrumbs = document.querySelector(".o_control_panel_breadcrumbs");
    if (!breadcrumbs) {
        return;
    }
    const fresh = root.querySelector(".o_form_statusbar .o_statusbar_buttons");
    if (!fresh) {
        // Already moved on an earlier render, and this render did not rebuild
        // it - the node Owl patches is the one sitting in the breadcrumb row.
        return;
    }
    // A rebuild leaves the previously relocated container orphaned: its render
    // is gone, so it would linger as a dead copy of the buttons.
    for (const stale of breadcrumbs.querySelectorAll(`.${RELOCATED}`)) {
        stale.remove();
    }
    const band = fresh.parentElement;
    fresh.classList.add(RELOCATED);
    // Placement, not just parentage. Two items on the breadcrumb row carry
    // margin-right:auto - the save indicator and a trailing spacer - and they
    // split the row's free space between them, ~144px each. Appending put the
    // buttons beyond both (310px from the name); inserting after the indicator
    // still left one of those margins in front of them (247px). So they go
    // immediately after the breadcrumb itself, ahead of every auto margin,
    // and the row reads name, buttons, then the indicator when it appears.
    const anchor = breadcrumbs.querySelector(".o_breadcrumb");
    if (anchor) {
        anchor.after(fresh);
    } else {
        breadcrumbs.append(fresh);
    }

    // The band is now empty but keeps its padding, so the form would show a
    // blank stripe where the buttons used to be.
    //
    // It has to be !important. Odoo builds the band with Bootstrap's d-flex,
    // which is `display: flex !important`, and that beats both a plain
    // stylesheet rule and a plain inline style - the element read as
    // display:flex with an inline display:none sitting on it. Setting the
    // priority explicitly is what actually wins.
    //
    // Done here rather than in SCSS so it stays beside the move that caused
    // it, and the effect re-runs every render, so Owl rebuilding the band
    // cannot leave a stripe behind.
    //
    // Only when nothing is left: a <header> can also hold plain fields, and
    // one that still has content has to keep rendering.
    if (band && !band.children.length) {
        band.style.setProperty("display", "none", "important");
    }
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.resModel !== MODEL) {
            return;
        }
        // No dependency list: Owl's default is [NaN], which never compares
        // equal, so the effect runs after every render. That is what is
        // wanted - the buttons are rebuilt on things a dependency list would
        // have to enumerate and would eventually miss, like status flipping
        // Cancel Schedule to Uncancel Schedule.
        useEffect(() => relocateHeaderButtons(this.rootRef && this.rootRef.el));
    },
});
