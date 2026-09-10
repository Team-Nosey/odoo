# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.8 - backfill Postlog overrun state.

The three new fields arrive empty, but postlogs are already attached to
hundreds of schedules and some of those are already over capacity. Without
this the Overruns tab reads zero on deploy and stays wrong until somebody
presses Refresh on every program and week.

Calls the model's own recompute rather than reimplementing the rule in SQL:
there is one definition of an overrun and this is not a second copy of it.

Scoped to schedules that actually carry an attached, non-removed postlog -
there is nothing to compute for the rest, and the write would be a no-op.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT DISTINCT schedule
          FROM mv_spot_data
         WHERE schedule IS NOT NULL
           AND removed IS NOT TRUE
        """
    )
    schedule_ids = [row[0] for row in cr.fetchall()]
    if not schedule_ids:
        return

    env['mv.spot_data']._recompute_postlog_overruns(schedule_ids)

    cr.execute(
        """
        SELECT count(*), COALESCE(sum(postlog_overrun_amount), 0)
          FROM mv_schedules
         WHERE postlog_overrun_amount > 0
        """
    )
    over_count, over_units = cr.fetchone()
    _logger.info(
        "mv_spot_data: recomputed overruns for %s schedule(s); "
        "%s over capacity by %s unit(s) in total",
        len(schedule_ids), over_count, over_units,
    )
