# -*- coding: utf-8 -*-
"""Post-migration for 19.0.1.2.5 - Prelog Workbench indexes.

The workbench filters on some combination of
    import_program + import_week_value + version + removed + schedule
on every request, and the overrun map groups by `schedule`.

Odoo creates single-column indexes for the fields we marked
`index=True` (version, schedule). This adds the composite index for the
three-way filter that fronts every workbench query, plus a partial
index for the very common "not removed" predicate. Composite / partial
indexes cannot be expressed through the ORM field definition, hence
raw DDL here.

CONCURRENTLY is deliberately NOT used: Odoo runs migrations inside a
transaction and CREATE INDEX CONCURRENTLY cannot run there. On a large
table this will hold a write lock for the duration - acceptable during
an upgrade window.

Idempotent: IF NOT EXISTS on every statement.
"""
import logging

_logger = logging.getLogger(__name__)

_INDEXES = (
    # Main workbench filter.
    (
        'mv_prelog_data_workbench_filter_idx',
        'mv_prelog_data (import_program, import_week_value, version)',
        None,
    ),
    # Overrun map: WHERE schedule IN (...) AND removed = FALSE GROUP BY schedule
    (
        'mv_prelog_data_schedule_active_idx',
        'mv_prelog_data (schedule)',
        'COALESCE(removed, FALSE) = FALSE',
    ),
    # Default ordering of the workbench result set.
    (
        'mv_prelog_data_airdate_order_idx',
        'mv_prelog_data (airdate, scheduletime, id)',
        None,
    ),
)


def migrate(cr, version):
    if not version:
        return
    for name, target, where in _INDEXES:
        stmt = 'CREATE INDEX IF NOT EXISTS %s ON %s' % (name, target)
        if where:
            stmt += ' WHERE %s' % where
        try:
            cr.execute(stmt)
            _logger.info('Prelog Workbench index ensured: %s', name)
        except Exception:
            # A failed index must not abort the whole upgrade - the
            # feature still works, just slower.
            _logger.exception(
                'Could not create Prelog Workbench index %s', name,
            )
            cr.rollback()
