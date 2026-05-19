# -*- coding: utf-8 -*-
"""Marathon Ventures internal knowledge base.

Stores training material from Salesforce (PDFs + structured walkthroughs)
so users can browse SOPs from inside Odoo. Sourced from the Salesforce
training PDF library: getting-started, communication, email-etiquette,
ops-protocols, gmail-templates, etc.
"""

from odoo import api, fields, models


class MarathonKnowledgeSection(models.Model):
    """A top-level grouping (Operations, Sales, Billing, Communication ...)."""

    _name = 'marathon.knowledge.section'
    _description = 'Marathon Knowledge Section'
    _order = 'sequence, name'

    name = fields.Char(string='Section', required=True, translate=True)
    code = fields.Char(string='Code', help='Internal short code')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    article_ids = fields.One2many(
        'marathon.knowledge.article', 'section_id', string='Articles',
    )
    article_count = fields.Integer(
        string='# Articles', compute='_compute_article_count',
    )
    active = fields.Boolean(string='Active', default=True)

    @api.depends('article_ids')
    def _compute_article_count(self):
        for r in self:
            r.article_count = len(r.article_ids)


class MarathonKnowledgeArticle(models.Model):
    """A single SOP / training article. Body is HTML so we can inline
    structured walk-throughs; a PDF attachment is also retained for
    downloadability."""

    _name = 'marathon.knowledge.article'
    _description = 'Marathon Knowledge Article'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'section_id, sequence, name'

    name = fields.Char(string='Title', required=True, tracking=True)
    section_id = fields.Many2one(
        'marathon.knowledge.section', string='Section',
        required=True, ondelete='restrict', tracking=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    summary = fields.Char(string='Summary')
    body = fields.Html(string='Body', sanitize=True)
    pdf_filename = fields.Char(string='PDF Filename')
    pdf_attachment = fields.Binary(string='PDF Attachment')
    tag_ids = fields.Many2many(
        'marathon.knowledge.tag', string='Tags',
    )
    related_model = fields.Char(
        string='Related Odoo Model',
        help='Optional reference to the Odoo model this article documents.',
    )
    audience = fields.Selection(
        [
            ('all', 'All Users'),
            ('planner', 'Planners'),
            ('assistant', 'Assistants'),
            ('ae', 'Account Executives'),
            ('finance', 'Finance'),
            ('ops', 'Operations'),
        ],
        string='Audience', default='all', tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        string='Status', default='published', tracking=True,
    )
    last_reviewed_date = fields.Date(string='Last Reviewed')

    def action_publish(self):
        self.write({'state': 'published'})

    def action_archive_article(self):
        self.write({'state': 'archived'})


class MarathonKnowledgeTag(models.Model):
    _name = 'marathon.knowledge.tag'
    _description = 'Marathon Knowledge Tag'
    _order = 'name'

    name = fields.Char(string='Tag', required=True)
    color = fields.Integer(string='Color')
