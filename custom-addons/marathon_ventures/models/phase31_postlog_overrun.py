# -*- coding: utf-8 -*-
"""Phase 31 - Postlog / Schedule overrun detection.

A schedule sells `units_available` spots. When more postlogs than that are
attached to it, the network over-delivered - or the matcher attached spots that
belong somewhere else. Either way the operator needs to see it.

    overrun = max(0, non-removed postlogs attached - units_available)

Removed rows do not count. That is what makes Remove the fix for a false
overrun: take the duplicate or bonus airings out of reconciliation and the
count drops.

Under-delivery is deliberately not surfaced. max(0, ...) floors at zero.

Design
------
Three stored fields, no computes:

    mv.spot_data.is_overrun               per row, indexed
    mv.schedules.postlog_attached_count   per schedule
    mv.schedules.postlog_overrun_amount   per schedule

Stored rather than derived per request because the Overruns tab needs a count,
a filter and a sort, and those have to be SQL. This is the same reasoning that
put the match result on the row.

`is_overrun` is True for EVERY attached row of an over-capacity schedule, not
for the last N. "Which spot is the overage" has no defensible answer among
identical airings, and hiding the rest would make the tab useless - the
operator has to see all of them to decide which to remove.

Recompute always processes a whole schedule. A row's Info line names the
schedule's figures, so every row on that schedule changes together.

Deliberately separate from prelog
---------------------------------
mv.schedules already carries `overrun_amount` and `prelog_attached_count` from
phase29. Those are prelog's. Sharing them would mean the two workbenches
overwriting each other's numbers on the same record, silently, with the last
writer winning - so postlog gets its own pair and phase29 is untouched.

There is no override of mv.schedules.write() here either. When somebody edits a
schedule's units_available, nothing in the postlog population moved but the
overrun changed; that is picked up by the workbench's Refresh, which recomputes
its whole program/week. Refresh costs one grouped query and keeps us out of a
shared model's write path.
"""
import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class MvSchedulesPostlogOverrun(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    postlog_attached_count = fields.Integer(
        string='Attached Postlogs',
        default=0,
        help='Count of non-removed Postlog Data rows attached to this schedule.',
    )
    # Shows "Never run" beside Units Preempted, and nothing once a run has
    # covered this schedule's week.
    #
    # Units Preempted is a Float, and Odoo represents a NULL Float as 0.0 - so
    # the field cannot tell "nothing was preempted" from "preemptions were never
    # run". Rather than replace it (you would lose the ability to type one by
    # hand), this sits next to it and is empty unless there is something to say.
    #
    # The NULL is read from the column: no Python-side check can see it, since
    # the ORM hands back 0.0 either way.
    units_preempted_state = fields.Char(
        string='Preemptions',
        compute='_compute_units_preempted_state',
        store=False,
        help=(
            'Reads "Never run" until Run Preemptions has covered this '
            "schedule's week. Units Preempted shows 0.0 both when nothing was "
            'preempted and when the run never happened; this is what tells '
            'them apart.'
        ),
    )

    def _compute_units_preempted_state(self):
        raw = {}
        if self.ids:
            # Pending writes are not in the table yet, and this has to reflect
            # them - a schedule preempted a moment ago must not read "Never run".
            self.env.flush_all()
            self.env.cr.execute(
                "SELECT id, units_preempted FROM mv_schedules WHERE id IN %s",
                (tuple(self.ids),),
            )
            raw = dict(self.env.cr.fetchall())
        for record in self:
            record.units_preempted_state = (
                _('Never run') if raw.get(record.id) is None else ''
            )

    postlog_overrun_amount = fields.Integer(
        string='Postlog Overrun',
        default=0,
        help=(
            'How many attached Postlog Data rows exceed units_available. '
            'Zero when within capacity - under-delivery is not reported here.'
        ),
    )


class MvSpotDataOverrun(models.Model):
    _name = 'mv.spot_data'
    _inherit = 'mv.spot_data'

    def unlink(self):
        """Deleting rows frees capacity, so the schedules they leave behind need
        recomputing. Collect them before the delete, recompute after."""
        schedule_ids = set(self.mapped('schedule').ids)
        result = super().unlink()
        if schedule_ids:
            self._recompute_postlog_overruns(schedule_ids)
        return result

    @api.model
    def _recompute_postlog_overruns(self, schedule_ids):
        """Recompute overrun state for each given schedule. Idempotent.

        Callers pass the schedules that may have gained or lost an attachment;
        each is recomputed from scratch rather than adjusted, so a missed hook
        costs a stale number rather than a wrong one that compounds.

        Returns what changed - {'schedules': n, 'flagged': n, 'cleared': n} -
        so a caller can tell the operator. Refresh needs this: correcting a
        schedule's units and pressing Refresh does no matching work at all, and
        without a count it reported "nothing to re-check" while fixing exactly
        what it had been asked to fix.
        """
        summary = {'schedules': 0, 'flagged': 0, 'cleared': 0}
        ids = {int(i) for i in (schedule_ids or []) if i}
        if not ids:
            return summary

        schedules = self.env['mv.schedules'].browse(sorted(ids)).exists()
        for schedule in schedules:
            attached = self.search([
                ('schedule', '=', schedule.id),
                ('removed', '=', False),
            ])
            count = len(attached)
            cap = int(schedule.units_available or 0)
            # A cap of zero means "no capacity recorded", not "sold nothing".
            # Every one of the 8,793 real schedules carries units_available, so
            # treating 0 as a real cap changes nothing in production - but it
            # would flag every spot on any schedule whose units were missing,
            # which is a false positive on incomplete data rather than a finding.
            # (This is exactly what makes six prelog tests fail: their fixtures
            # omit units_available, so the cap is 0 and every row overruns.)
            overrun = max(0, count - cap) if cap > 0 else 0

            vals = {}
            if schedule.postlog_attached_count != count:
                vals['postlog_attached_count'] = count
            if schedule.postlog_overrun_amount != overrun:
                vals['postlog_overrun_amount'] = overrun
            if vals:
                # sudo: an operator with workbench access may not have write
                # rights on Schedules, and this is a derived figure, not an edit.
                schedule.sudo().write(vals)
                summary['schedules'] += 1

            # The flag, and the Info line that explains it, are the same fact
            # said twice - so they are written together, for every row on the
            # schedule.
            info = self._postlog_overrun_info(schedule, count, overrun)
            for postlog in attached:
                row_vals = {}
                if postlog.is_overrun != bool(overrun):
                    row_vals['is_overrun'] = bool(overrun)
                if overrun and postlog.info != info:
                    row_vals['info'] = info
                elif not overrun and postlog.is_overrun:
                    # Back within capacity: drop the line this feature wrote.
                    # A matched row says nothing in Info by default.
                    row_vals['info'] = False
                if row_vals:
                    postlog.write(row_vals)
                    if 'is_overrun' in row_vals:
                        summary[
                            'flagged' if row_vals['is_overrun'] else 'cleared'
                        ] += 1
        return summary

    @api.model
    def _postlog_overrun_info(self, schedule, count, overrun):
        """The Info line for a row on an over-capacity schedule.

        Describes the schedule, not the row - which is why it reads identically
        on every row attached to that schedule, and why they are all rewritten
        together when the count changes.
        """
        if not overrun:
            return False
        return _(
            'Schedule %(name)s has %(cap)s unit(s) but %(count)s postlog(s) '
            'attached - over by %(overrun)s.'
        ) % {
            'name': schedule.display_name or '',
            'cap': int(schedule.units_available or 0),
            'count': count,
            'overrun': overrun,
        }
