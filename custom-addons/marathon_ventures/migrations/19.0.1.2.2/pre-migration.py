# -*- coding: utf-8 -*-
"""Deal object cleanup pre-migration (13 unused fields removed).

Runs BEFORE Odoo re-syncs the schema for module 'marathon_ventures'
version 19.0.1.2.2.

Removed from mv.deal in code: ltc_date, restricted_programming_dna,
digital_id, rate, budget_30, max_sep, max_day, quarter, year, priority,
test_pp, contact_email, deal_count. The mv.restricted_programming_dna.tag
model was removed with its m2m field (it had no other users).

DELIBERATELY NOT DONE HERE: dropping the mv_deal columns, the
mv_deal_restricted_programming_dna_rel table or the
mv_restricted_programming_dna_tag table. The columns stay as a safety
net until the object/layout cleanup (deal + schedules) has settled;
a later migration will drop them in one pass.

The only manual work needed now is purging the stale cached arch of the
phase9 layout INHERIT view. Odoo loads data files in manifest order and
validates the base view against ALL inherits AT UPSERT TIME - if the DB
still holds the old phase9 arch referencing the removed fields, the
base-view upsert crashes ("Field ... does not exist"). Deleting the
stale record forces Odoo to recreate it fresh from the current XML
later in the same load pass. Only INHERIT views may be deleted - the
base view is protected by the RESTRICT FK on ir_ui_view.inherit_id.

This script is idempotent: re-runs on a DB that's already been purged
are a no-op.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install (no previous version): nothing to migrate.
        return

    for xmlid in ('view_mv_deal_form_phase9_layout',):
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
    _logger.info('Deal cleanup migration: stale phase9 deal layout view purged')
