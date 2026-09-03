# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.7 - stored Postlog matching.

Carries the work of BOTH version bumps on this branch. 19.0.1.2.6 had its own
post-migration during development; the two were merged here on review, so the
gap in the migrations directory between 1.2.5 and 1.2.7 is deliberate and
nothing is missing.

Merging them is safe because they do not depend on each other: job 1 rewrites
`import_match_status`, and jobs 2 and 3 key on `schedule` and `match_flags` and
never read that column. All three are idempotent, so a database that already
ran the old 19.0.1.2.6 script simply matches no rows on the first job.

Three jobs.

1. `mv_spot_data.import_match_status` loses `created_without_schedule` in favour
   of `unmatched`. The selection is validated on write, not on read, so existing
   rows would keep an out-of-selection value and show blank in the UI until
   touched.

   `failed_to_create` is dropped from the selection entirely - it was declared
   but never written, and could not be: a row that fails to be created has no
   record to carry a status. Remapped defensively anyway in case a row was ever
   hand-edited.

2. Rows that reached the No Suggestion tab stored no `info` at all, so the
   column was blank on exactly the rows whose problem needs naming. Filled from
   the flag that put them there.

3. Rows attached by hand in the Workbench kept the `info` and
   `possible_schedules` written at import, so Info read "3 suggestion(s)" beside
   a Matched badge and the candidate JSON stayed on a row nobody will review
   again. Cleared.

All three are postlog only - mv_prelog_data is not touched.

The workbench's composite indexes were created in a post-migration too. They now
live in mv.spot_data.init(), because a post-migration does not run on install -
so a freshly created database had none of them while an upgraded one had all
three.

The wording in job 2 must match mv.spot_data._postlog_info_text. It is
duplicated here rather than imported because a migration runs against the *old*
module code on disk only by accident of timing; SQL that says what it means is
safer than a call into a model that may not yet be reloaded.
"""
import logging

_logger = logging.getLogger(__name__)

_STATUS_REMAP = (
    ('created_without_schedule', 'unmatched'),
    ('failed_to_create', 'unmatched'),
)

_INFO_BACKFILL = (
    ('missing_deal', 'Missing deal number'),
    ('no_schedules', 'No schedules found for deal number'),
    ('missing_air_date', 'Missing air date'),
)


def migrate(cr, version):
    if not version:
        return

    # 1. Retire the old status codes (was 19.0.1.2.6).
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

    # 2. Name the reason on rows that have none.
    for token, text in _INFO_BACKFILL:
        cr.execute(
            """
            UPDATE mv_spot_data
               SET info = %s
             WHERE schedule IS NULL
               AND match_flags LIKE %s
               AND (info IS NULL OR info = '')
            """,
            (text, '%%,%s,%%' % token),
        )
        if cr.rowcount:
            _logger.info(
                "mv_spot_data: filled info on %s row(s) flagged %s",
                cr.rowcount, token,
            )

    # 3. A matched row advertises nothing.
    cr.execute(
        """
        UPDATE mv_spot_data
           SET info = NULL,
               possible_schedules = NULL
         WHERE schedule IS NOT NULL
           AND (info IS NOT NULL OR possible_schedules IS NOT NULL)
        """
    )
    if cr.rowcount:
        _logger.info(
            "mv_spot_data: cleared stale suggestion state from %s matched row(s)",
            cr.rowcount,
        )
