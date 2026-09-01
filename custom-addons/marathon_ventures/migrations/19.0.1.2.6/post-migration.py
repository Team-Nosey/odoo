# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.6 - stored Postlog matching.

Two jobs.

1. `mv_spot_data.import_match_status` loses `created_without_schedule` in
   favour of `unmatched`. The selection is validated on write, not on read, so
   existing rows would keep an out-of-selection value and show blank in the UI
   until touched. Remapped here.

   `failed_to_create` is dropped from the selection entirely - it was declared
   but never written, and could not be: a row that fails to be created has no
   record to carry a status. Remapped defensively anyway in case a row was ever
   hand-edited.

2. Composite indexes for the Postlog Workbench, mirroring what 19.0.1.2.5 did
   for prelog. Every workbench request filters on
   import_program + import_week_value, then narrows by match status and by
   whether a suggestion exists. Odoo creates the single-column indexes for the
   fields marked index=True; these are the multi-column ones the ORM cannot
   express.

CONCURRENTLY is deliberately NOT used - Odoo runs migrations inside a
transaction and CREATE INDEX CONCURRENTLY cannot. On a large table this holds a
write lock for the duration, which is acceptable during an upgrade window.

Idempotent: the UPDATE is a no-op once remapped, and every index uses
IF NOT EXISTS.
"""
import logging

_logger = logging.getLogger(__name__)

_STATUS_REMAP = (
    ('created_without_schedule', 'unmatched'),
    ('failed_to_create', 'unmatched'),
)

_INDEXES = (
    # Fronts every workbench request.
    (
        'mv_spot_data_workbench_filter_idx',
        'mv_spot_data (import_program, import_week_value, import_match_status)',
    ),
    # The Suggestions / No Suggestion tabs: unmatched rows split by whether a
    # suggestion exists. Partial, because matched rows are the large majority
    # and are never queried this way.
    (
        'mv_spot_data_suggestion_idx',
        'mv_spot_data (import_program, import_week_value, suggested_schedule) '
        "WHERE import_match_status = 'unmatched'",
    ),
    # Default ordering of the list.
    (
        'mv_spot_data_airdate_order_idx',
        'mv_spot_data (air_date, air_time, id)',
    ),
)


def migrate(cr, version):
    if not version:
        return

    for old_value, new_value in _STATUS_REMAP:
        cr.execute(
            "UPDATE mv_spot_data SET import_match_status = %s "
            "WHERE import_match_status = %s",
            (new_value, old_value),
        )
        if cr.rowcount:
            _logger.info(
                "mv_spot_data: remapped %s row(s) from %s to %s",
                cr.rowcount, old_value, new_value,
            )

    for name, definition in _INDEXES:
        cr.execute("CREATE INDEX IF NOT EXISTS %s ON %s" % (name, definition))
        _logger.info("mv_spot_data: ensured index %s", name)
