# -*- coding: utf-8 -*-
"""Phase 27 - Auto-sync program_daypart when Schedule times change.

Requirement:
  When a Schedule record is edited and its Start Time or End Time is
  modified, the Program Daypart field should be recalculated and
  updated automatically. The calculation should use the same
  containment logic that is currently implemented for the Units
  Report save flow (`mv.deal._resolve_daypart_label`).

The Units Report save flow already writes `program_daypart`, so this
hook is only strictly needed for the OTHER paths that mutate schedule
times - the Schedule form's Start Time / End Time widgets, mass
updates, external RPC callers, and the backfill migration.

Recursion note:
  The inner write we issue only touches `program_daypart`, never
  start_time / end_time, so the outer `times_changed` branch does
  not re-enter. We also call `super().write(...)` on the inner
  update to bypass our own override entirely.
"""
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MvSchedulesAutoDaypart(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    # Re-declare original_rate with default=False so new schedules
    # land with NULL instead of the Monetary field's stock 0.0
    # default. The rate-history capture in write() below is what
    # populates it later.
    original_rate = fields.Monetary(
        string='Original Rate',
        currency_field='currency_id',
        default=False,
    )

    # ------------------------------------------------------------------
    # Create: fill program_daypart when the caller did not set it,
    # and force original_rate to NULL when the caller did not pass
    # one (Monetary's ORM layer would otherwise coerce it to 0.0).
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        explicit_orig = [('original_rate' in v) for v in vals_list]

        records = super().create(vals_list)

        ids_to_null = [
            rec.id
            for rec, had_explicit in zip(records, explicit_orig)
            if not had_explicit
        ]
        if ids_to_null:
            self.env.cr.execute(
                "UPDATE mv_schedules SET original_rate = NULL "
                "WHERE id = ANY(%s)",
                (ids_to_null,),
            )
            records.invalidate_recordset(['original_rate'])

        for rec in records:
            if rec.program_daypart:
                continue          # caller (e.g. Units Grid save) set it
            self._mv_backfill_program_daypart_on(rec)
        return records

    # ------------------------------------------------------------------
    # Write: whenever times change and the caller is not explicitly
    # setting program_daypart, recompute and store it. Also snapshots
    # the pre-change Rate into Original Rate the FIRST time the rate
    # changes on a schedule (rate-history requirement).
    # ------------------------------------------------------------------
    def write(self, vals):
        times_changed = ('start_time' in vals) or ('end_time' in vals)
        manual_daypart = ('program_daypart' in vals)

        # Rate-history capture: read the current Rate on every record
        # where original_rate is still empty and the incoming vals is
        # about to change the rate. We do this BEFORE super() runs so
        # the pre-change value is available. Stored as {rec.id: old}.
        pre_rates = {}
        if 'rate' in vals and 'original_rate' not in vals:
            try:
                new_rate = float(vals.get('rate') or 0.0)
            except (TypeError, ValueError):
                new_rate = 0.0
            for rec in self:
                if rec.original_rate:
                    continue                    # already frozen
                try:
                    cur_rate = float(rec.rate or 0.0)
                except (TypeError, ValueError):
                    cur_rate = 0.0
                if abs(cur_rate - new_rate) > 1e-6:
                    pre_rates[rec.id] = cur_rate

        result = super().write(vals)

        # Second phase: stamp Original Rate = captured pre-change rate.
        # super() bypasses our override -> no recursion.
        for rec in self:
            old = pre_rates.get(rec.id)
            if old is None:
                continue
            if rec.original_rate:                # someone else set it - respect
                continue
            super(MvSchedulesAutoDaypart, rec).write({'original_rate': old})

        if times_changed and not manual_daypart:
            for rec in self:
                self._mv_backfill_program_daypart_on(rec)
        return result

    # ------------------------------------------------------------------
    # Helper: compute and store program_daypart for one record.
    #
    # Delegates label resolution to mv.deal._resolve_daypart_label so
    # the containment logic + hardcoded fallback stays in exactly one
    # place. Passes daypart_key=None so the resolver walks:
    #   containment against deal.program.daypart_ids
    #   -> hardcoded key by _guess_daypart(start, end)
    #   -> 'Custom' final fallback.
    # ------------------------------------------------------------------
    def _mv_backfill_program_daypart_on(self, rec):
        if not rec.start_time or not rec.end_time:
            return
        deal = rec.deal_parent
        if not deal:
            return
        try:
            label = deal._resolve_daypart_label(
                None, rec.start_time, rec.end_time,
            )
        except Exception:
            _logger.exception(
                "Auto-daypart resolve failed for schedule id=%s "
                "(deal_id=%s, start=%s, end=%s)",
                rec.id, deal.id, rec.start_time, rec.end_time,
            )
            return
        if not label:
            return
        if (rec.program_daypart or '') == label:
            return
        # super() write bypasses our own override -> no recursion.
        super(MvSchedulesAutoDaypart, rec).write({
            'program_daypart': label,
        })
