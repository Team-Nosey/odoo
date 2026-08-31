# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.4

`mv.schedules.units_aired` was a stubbed compute that always stored
False (-> 0). It is now implemented as:

    canceled            -> 0
    otherwise           -> max(0, units_available - units_preempted)

Because the field is `store=True` and only the METHOD BODY changed
(not the field definition), Odoo will not recompute existing rows on
its own. This migration forces the recompute so Bundle Paperwork's
Excel Sheet2 column M (Total Units) stops resolving to 0 for every
schedule.

Done in SQL rather than via the ORM because the schedule table can be
large and the formula is a plain arithmetic expression - no need to
instantiate records. Odoo will keep it in sync from here on via the
@api.depends on status / units_available / units_preempted.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install: the compute runs naturally on create.
        return

    cr.execute("""
        UPDATE mv_schedules
           SET units_aired = CASE
                 WHEN status = 'canceled' THEN 0
                 ELSE GREATEST(
                     0,
                     COALESCE(units_available, 0) - COALESCE(units_preempted, 0)
                 )
               END
         WHERE units_aired IS NULL
            OR units_aired = 0
    """)
    _logger.info(
        'units_aired backfill: %s schedule row(s) recomputed',
        cr.rowcount,
    )
