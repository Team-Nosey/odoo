# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.6 - stored Postlog matching.

`mv_spot_data.import_match_status` loses `created_without_schedule` in favour of
`unmatched`. The selection is validated on write, not on read, so existing rows
would keep an out-of-selection value and show blank in the UI until touched.
Remapped here.

`failed_to_create` is dropped from the selection entirely - it was declared but
never written, and could not be: a row that fails to be created has no record
to carry a status. Remapped defensively anyway in case a row was ever
hand-edited.

The workbench's composite indexes used to be created here too. They now live in
mv.spot_data.init(), because a post-migration does not run on install - so a
freshly created database had none of them while an upgraded one had all three.
"""
import logging

_logger = logging.getLogger(__name__)

_STATUS_REMAP = (
    ('created_without_schedule', 'unmatched'),
    ('failed_to_create', 'unmatched'),
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

