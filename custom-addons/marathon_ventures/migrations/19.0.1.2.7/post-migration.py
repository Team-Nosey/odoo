# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.7 - backfill mv_spot_data.info.

`info` is derived entirely from `match_flags` and whether a schedule is
attached, so it can be rebuilt in SQL without re-running the matcher.

Two jobs.

1. Rows that reached the No Suggestion tab stored no `info` at all, so the
   column was blank on exactly the rows whose problem needs naming. Filled from
   the flag that put them there.

2. Rows attached by hand in the Workbench kept the `info` and
   `possible_schedules` written at import, so Info read "3 suggestion(s)" beside
   a Matched badge and the candidate JSON stayed on a row nobody will review
   again. Cleared.

Both are postlog only - mv_prelog_data is not touched.

The wording must match mv.spot_data._postlog_info_text. It is duplicated here
rather than imported because a migration runs against the *old* module code on
disk only by accident of timing; SQL that says what it means is safer than a
call into a model that may not yet be reloaded.
"""


def migrate(cr, version):
    if not version:
        return

    # 1. Name the reason on rows that have none.
    for token, text in (
        ('missing_deal', 'Missing deal number'),
        ('no_schedules', 'No schedules found for deal number'),
        ('missing_air_date', 'Missing air date'),
    ):
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

    # 2. A matched row advertises nothing.
    cr.execute(
        """
        UPDATE mv_spot_data
           SET info = NULL,
               possible_schedules = NULL
         WHERE schedule IS NOT NULL
           AND (info IS NOT NULL OR possible_schedules IS NOT NULL)
        """
    )
