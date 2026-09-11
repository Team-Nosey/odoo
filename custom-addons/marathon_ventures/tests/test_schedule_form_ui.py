from datetime import date

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestScheduleFormUI(HttpCase):
    """The Schedule form layout, driven through a browser.

    Most of the layout is arch and could be asserted by reading the view,
    but one piece cannot: the header buttons are moved onto the breadcrumb
    row by mv_schedule_header.js after Owl renders. Only a real browser
    shows whether that landed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.program = cls.env['mv.programs'].create({
            'name': 'Layout Test Network',
            'clientcode': 'LTN',
            'clock_start_time': 'v_6am',
        })
        # All seven days, which is what a real Late Night schedule carries -
        # and the case that made Days Allowed wrap onto three lines when the
        # timing row split its width evenly five ways.
        days = cls.env['mv.days_allowed.tag']
        for name in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
            days |= (
                cls.env['mv.days_allowed.tag'].search(
                    [('name', '=ilike', name + '%')], limit=1,
                )
                or cls.env['mv.days_allowed.tag'].create({'name': name})
            )
        cls.deal = cls.env['mv.deal'].create({
            'program': cls.program.id,
            'network_deal_number': 'LTN-1',
            'length': 'v_30',
        })
        cls.schedule = cls.env['mv.schedules'].create({
            'deal_parent': cls.deal.id,
            'week': date(2026, 7, 13),
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(days.ids)],
            'rate': 810.0,
            'status': 'sold',
            'units_available': 3.0,
        })

    def test_schedule_form_layout(self):
        action = self.env.ref('marathon_ventures.action_mv_schedules')
        self.start_tour(
            '/odoo/action-%s/%s' % (action.id, self.schedule.id),
            'mv_schedule_form_layout_tour',
            login='admin',
        )

    def test_a_new_schedule_still_opens(self):
        """The New button is gone; opening an unsaved record must not be."""
        action = self.env.ref('marathon_ventures.action_mv_schedules')
        self.start_tour(
            '/odoo/action-%s/new' % action.id,
            'mv_new_schedule_form_tour',
            login='admin',
        )

    def test_schedule_list_columns(self):
        """The list's columns, and what its show/hide menu offers."""
        action = self.env.ref('marathon_ventures.action_mv_schedules')
        self.start_tour(
            '/odoo/action-%s' % action.id,
            'mv_schedule_list_columns_tour',
            login='admin',
        )
