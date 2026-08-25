# -*- coding: utf-8 -*-

import base64
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from ..services.xlsx_renderer import render_short_form_workbook

_logger = logging.getLogger(__name__)


class MvPrelogConductorBatch(models.Model):
    _name = "mv.prelog.conductor.batch"
    _description = "Prelog Conductor Batch"
    _order = "create_date desc, id desc"

    name = fields.Char(default="New", required=True, copy=False, readonly=True)
    network_id = fields.Many2one(
        "mv.programs",
        string="Network",
        required=True,
        ondelete="restrict",
        index=True,
    )
    week = fields.Date(required=True, index=True)
    version = fields.Integer(required=True, index=True)
    requested_by_id = fields.Many2one(
        "res.users",
        string="Prepared By",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
    )
    recipient_ids = fields.One2many(
        "mv.prelog.conductor.recipient",
        "batch_id",
        string="Recipients",
    )
    state = fields.Selection(
        [
            ("preparing", "Preparing"),
            ("ready", "Ready"),
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("attention", "Needs Attention"),
        ],
        compute="_compute_summary",
        store=True,
        string="Status",
    )
    recipient_count = fields.Integer(compute="_compute_summary", store=True)
    prelog_count = fields.Integer(compute="_compute_summary", store=True)
    prepared_count = fields.Integer(compute="_compute_summary", store=True)
    missing_email_count = fields.Integer(compute="_compute_summary", store=True)
    failed_count = fields.Integer(compute="_compute_summary", store=True)
    queued_count = fields.Integer(compute="_compute_summary", store=True)
    sent_count = fields.Integer(compute="_compute_summary", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "mv.prelog.conductor.batch"
                ) or _("New")
        return super().create(vals_list)

    @api.depends(
        "recipient_ids.status",
        "recipient_ids.included",
        "recipient_ids.prelog_count",
    )
    def _compute_summary(self):
        for batch in self:
            lines = batch.recipient_ids
            statuses = set(lines.mapped("status"))
            batch.recipient_count = len(lines)
            batch.prelog_count = sum(lines.mapped("prelog_count"))
            batch.prepared_count = len(lines.filtered(lambda line: line.status == "prepared"))
            batch.missing_email_count = len(
                lines.filtered(lambda line: line.status == "missing_email")
            )
            batch.failed_count = len(lines.filtered(lambda line: line.status == "failed"))
            batch.queued_count = len(lines.filtered(lambda line: line.status == "queued"))
            batch.sent_count = len(lines.filtered(lambda line: line.status == "sent"))

            if not lines or statuses.intersection({"pending", "processing"}):
                batch.state = "preparing"
            elif "failed" in statuses:
                batch.state = "attention"
            elif "prepared" in statuses:
                batch.state = "ready"
            elif "queued" in statuses:
                batch.state = "queued"
            elif "missing_email" in statuses:
                batch.state = "attention"
            elif "sent" in statuses and statuses.issubset({"sent", "duplicate"}):
                batch.state = "sent"
            else:
                batch.state = "ready"

    def action_send_all(self):
        self.ensure_one()
        lines = self.recipient_ids.filtered(
            lambda line: line.included and line.status == "prepared"
        )
        if not lines:
            raise UserError(_("There are no included, prepared emails to send."))
        return lines.action_send_selected()

    def action_open_recipients(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "marathon_short_form_prelogs.action_mv_prelog_conductor_recipient"
        )
        action["domain"] = [("batch_id", "=", self.id)]
        action["context"] = {"default_batch_id": self.id, "create": False}
        return action


class MvPrelogConductorRecipient(models.Model):
    _name = "mv.prelog.conductor.recipient"
    _description = "Prelog Conductor Recipient"
    _order = "batch_id desc, contact_id, id"

    batch_id = fields.Many2one(
        "mv.prelog.conductor.batch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    network_id = fields.Many2one(
        related="batch_id.network_id",
        store=True,
        readonly=True,
        index=True,
    )
    week = fields.Date(related="batch_id.week", store=True, readonly=True, index=True)
    version = fields.Integer(
        related="batch_id.version", store=True, readonly=True, index=True
    )
    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        required=True,
        ondelete="restrict",
        index=True,
    )
    account_id = fields.Many2one(
        "res.partner",
        string="Account / Agency",
        ondelete="set null",
        index=True,
    )
    email = fields.Char(string="Email")
    included = fields.Boolean(default=True, string="Include")
    prelog_ids = fields.Many2many(
        "mv.prelog_data",
        "mv_prelog_conductor_recipient_prelog_rel",
        "recipient_id",
        "prelog_id",
        string="Prelogs",
        readonly=True,
    )
    prelog_count = fields.Integer(string="Prelog Rows", required=True, readonly=True)
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Attachment",
        readonly=True,
        ondelete="set null",
    )
    attachment_filename = fields.Char(
        related="attachment_id.name", string="Attachment Filename", readonly=True
    )
    email_subject = fields.Char(string="Subject", required=True)
    email_body = fields.Html(string="Body", required=True, sanitize=True)
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Generating"),
            ("prepared", "Prepared"),
            ("missing_email", "Missing Email"),
            ("failed", "Failed"),
            ("duplicate", "Already Exists"),
            ("queued", "Queued"),
            ("sent", "Sent"),
        ],
        default="pending",
        required=True,
        readonly=True,
        index=True,
    )
    error_message = fields.Text(string="Error", readonly=True)
    duplicate_of_id = fields.Many2one(
        "mv.prelog.conductor.recipient",
        string="Existing Result",
        readonly=True,
        ondelete="set null",
    )
    mail_id = fields.Many2one(
        "mail.mail", string="Outgoing Message", readonly=True, ondelete="set null"
    )
    attempt_count = fields.Integer(default=0, readonly=True)
    rendered_at = fields.Datetime(readonly=True)
    queued_at = fields.Datetime(readonly=True)
    sent_at = fields.Datetime(readonly=True)

    def action_download_attachment(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("This recipient does not have a generated workbook yet."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
            "target": "self",
        }

    def action_send_selected(self):
        candidates = self.filtered(
            lambda line: line.included
            and line.status == "prepared"
            and line.email
            and line.attachment_id
        )
        if not candidates:
            raise UserError(_("Select at least one included, prepared recipient."))

        sent = 0
        failures = 0
        for line in candidates:
            try:
                with self.env.cr.savepoint():
                    mail = self.env["mail.mail"].create(line._mail_values())
                    mail.send(raise_exception=False)

                    if mail.state == "sent":
                        line.write(
                            {
                                "mail_id": mail.id,
                                "status": "sent",
                                "queued_at": False,
                                "sent_at": fields.Datetime.now(),
                                "error_message": False,
                            }
                        )
                        sent += 1
                    else:
                        failure_reason = mail.failure_reason or _(
                            "The email was not accepted for immediate delivery."
                        )
                        # Never leave this message for the scheduled queue. If an
                        # SMTP server deferred it, record the failure and require
                        # an intentional retry from the recipient row.
                        if mail.state == "outgoing":
                            mail.write({"state": "cancel", "scheduled_date": False})
                        line.write(
                            {
                                "mail_id": mail.id,
                                "status": "failed",
                                "queued_at": False,
                                "sent_at": False,
                                "error_message": failure_reason,
                            }
                        )
                        failures += 1
            except Exception as exc:  # keep processing the selected recipients
                _logger.exception("Could not send Prelog Conductor recipient %s", line.id)
                line.write(
                    {
                        "status": "failed",
                        "queued_at": False,
                        "sent_at": False,
                        "error_message": str(exc),
                    }
                )
                failures += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Prelog Conductor"),
                "message": _("Sent %(sent)s email(s); %(failed)s failed.")
                % {"sent": sent, "failed": failures},
                "type": "success" if not failures else "warning",
                "sticky": False,
            },
        }

    def _mail_values(self):
        self.ensure_one()
        return {
            "subject": self.email_subject,
            "body_html": self.email_body,
            "email_to": self.email,
            "email_from": (
                self.env.company.email_formatted
                or self.batch_id.requested_by_id.email_formatted
                or False
            ),
            "attachment_ids": [Command.set(self.attachment_id.ids)],
            "model": self._name,
            "res_id": self.id,
            "auto_delete": False,
        }

    def action_retry_generation(self):
        failed = self.filtered(lambda line: line.status == "failed")
        if not failed:
            raise UserError(_("Select at least one failed recipient."))
        failed._reset_for_generation()
        return True

    def action_regenerate(self):
        if any(line.status in {"processing", "queued"} for line in self):
            raise UserError(
                _("Generating or queued recipients cannot be regenerated yet.")
            )
        self._reset_for_generation()
        return True

    def _reset_for_generation(self):
        for line in self:
            old_attachment = line.attachment_id
            keep_old_attachment = bool(line.mail_id)
            current_email = (line.contact_id.email or "").strip()
            line.write(
                {
                    "email": current_email or False,
                    "included": bool(current_email),
                    "attachment_id": False,
                    "mail_id": False,
                    "status": "pending",
                    "error_message": False,
                    "duplicate_of_id": False,
                    "rendered_at": False,
                    "queued_at": False,
                    "sent_at": False,
                }
            )
            if old_attachment and not keep_old_attachment:
                old_attachment.unlink()

    @api.model
    def _cron_process_prelog_conductor(self):
        self._sync_mail_statuses()
        lines = self.search(
            [("status", "=", "pending")], order="create_date, id", limit=10
        )
        for line in lines:
            line.write(
                {
                    "status": "processing",
                    "attempt_count": line.attempt_count + 1,
                    "error_message": False,
                }
            )
            try:
                with self.env.cr.savepoint():
                    line._generate_workbook()
            except Exception as exc:
                _logger.exception(
                    "Workbook generation failed for Prelog Conductor recipient %s",
                    line.id,
                )
                line.write({"status": "failed", "error_message": str(exc)})
        self._sync_mail_statuses()

    @api.model
    def _sync_mail_statuses(self):
        lines = self.search([("status", "=", "queued"), ("mail_id", "!=", False)])
        for line in lines:
            if line.mail_id.state == "sent":
                line.write(
                    {
                        "status": "sent",
                        "sent_at": fields.Datetime.now(),
                        "error_message": False,
                    }
                )
            elif line.mail_id.state in {"exception", "cancel"}:
                line.write(
                    {
                        "status": "failed",
                        "error_message": line.mail_id.failure_reason
                        or _("The queued email was cancelled or failed."),
                    }
                )

    def _generate_workbook(self):
        self.ensure_one()
        if not self.prelog_ids:
            raise UserError(_("No prelog rows are attached to this recipient."))

        workbook_bytes, filename = render_short_form_workbook(self)
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(workbook_bytes),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        self.write(
            {
                "attachment_id": attachment.id,
                "status": "prepared" if self.email else "missing_email",
                "included": bool(self.email),
                "rendered_at": fields.Datetime.now(),
                "error_message": False,
            }
        )
