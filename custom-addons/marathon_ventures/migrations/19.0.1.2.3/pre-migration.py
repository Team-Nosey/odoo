# -*- coding: utf-8 -*-
"""Schedule object/layout cleanup pre-migration.

Runs BEFORE Odoo re-syncs the schema for module 'marathon_ventures'
version 19.0.1.2.3.

Removed from mv.schedules in code: daypart (stub compute, always blank)
plus the phase 9 UI helpers additional_weeks / end_week_auto /
show_advanced_schedule and the action_toggle_advanced_schedule method
(the Advanced collapse section is gone from the redesigned form).
`networks` stays on the object - it was only dropped from the layout.

As with the 19.0.1.2.2 deal cleanup, columns are deliberately NOT
dropped here; a later migration will sweep all dead columns at once.

The stale cached arch of the phase 9 schedule layout INHERIT view still
references the removed fields and the removed toggle method, so the
base-view upsert would crash at load time. Purge it so Odoo recreates
it fresh from the current XML. Only INHERIT views may be deleted - the
base view is protected by the RESTRICT FK on ir_ui_view.inherit_id.

This script is idempotent: re-runs on a DB that's already been purged
are a no-op.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    for xmlid in ('view_mv_schedules_form_phase9_layout',):
        cr.execute("""
            DELETE FROM ir_ui_view
             WHERE id IN (
                SELECT res_id FROM ir_model_data
                 WHERE module = 'marathon_ventures'
                   AND name = %s
                   AND model = 'ir.ui.view'
             )
        """, (xmlid,))
        cr.execute("""
            DELETE FROM ir_model_data
             WHERE module = 'marathon_ventures'
               AND name = %s
               AND model = 'ir.ui.view'
        """, (xmlid,))
    _logger.info('Schedule cleanup migration: stale phase9 schedule layout view purged')
