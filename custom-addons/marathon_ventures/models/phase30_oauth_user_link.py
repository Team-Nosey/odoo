# -*- coding: utf-8 -*-
"""Phase 30 - Link Google (OAuth) logins to EXISTING Odoo users.

Problem
-------
Stock `auth_oauth` resolves an OAuth login purely by `oauth_uid` (the
provider's subject id):

    oauth_user = self.search([("oauth_uid", "=", oauth_uid),
                              ('oauth_provider_id', '=', provider)])
    if not oauth_user:
        raise AccessDenied()

An Odoo user created normally has `oauth_uid` empty, so the very first
Google sign-in never matches. Odoo then falls through to `signup()`;
with signup disabled that raises SignupError -> AccessDenied ->
`/web/login?oauth_error=3`, rendered as:

    "You do not have access to this database or your invitation has
     expired..."

which is misleading - nothing is expired, the identity simply was
never linked.

Solution
--------
Resolve the user ourselves BEFORE delegating to super():

  1. Already-linked user (oauth_uid + provider) - the normal path.
  2. Otherwise fall back to matching an EXISTING, ACTIVE user by the
     provider-asserted email, then permanently store `oauth_uid` on
     that user so step 1 handles every later login.

Deliberately runs before super() rather than catching its
AccessDenied: super()'s except-branch calls signup(), which - if
signup is ever enabled - would create a DUPLICATE user instead of
linking the existing one.

Security
--------
Email-based linking is an account-takeover vector if applied naively,
so it is gated:

  * The provider must assert `email_verified` (Google's v3 userinfo
    endpoint returns this; scope `openid profile email` is already
    configured on the stock provider record). An unverified email is
    never trusted.
  * Exactly one active user must match; 0 or 2+ is refused rather than
    guessed at.
  * Only EXISTING users are linked. This module never creates a user,
    so an unknown Google account still cannot get in.
  * Optional domain allow-list, `mv_auth_oauth.allowed_domains`
    (comma-separated, e.g. "mvmediasales.com"). Empty = any domain,
    which is still safe because the user must already exist.
  * Linking is one-shot: once `oauth_uid` is set, the fast path owns
    that user and the email fallback is not consulted again.

Config parameters
-----------------
  mv_auth_oauth.link_by_email    '1' (default) | '0' to disable
  mv_auth_oauth.allowed_domains  '' (default)  | 'a.com,b.com'
"""
import logging

from odoo import models, api, _
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsersOAuthLink(models.Model):
    _inherit = 'res.users'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _mv_oauth_link_enabled(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'mv_auth_oauth.link_by_email', '1',
        )
        return str(param).strip().lower() not in ('0', 'false', 'no', '')

    @api.model
    def _mv_oauth_allowed_domains(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'mv_auth_oauth.allowed_domains', '',
        ) or ''
        return {
            part.strip().lower()
            for part in raw.split(',')
            if part.strip()
        }

    @api.model
    def _mv_oauth_email_is_verified(self, validation):
        """Google's v3 userinfo returns a JSON bool; the tokeninfo
        endpoint returns the string "true"; some providers omit it.
        """
        value = validation.get('email_verified')
        if value is None:
            # Some providers use this legacy spelling.
            value = validation.get('verified_email')

        if value is None:
            # Claim absent entirely. Only trust the email if an admin
            # has explicitly opted in AND pinned an allow-list, so a
            # stray gmail.com address can never match an internal user.
            ICP = self.env['ir.config_parameter'].sudo()
            trust = str(ICP.get_param(
                'mv_auth_oauth.trust_unverified_email', '0',
            )).strip().lower() in ('1', 'true', 'yes')
            return bool(trust and self._mv_oauth_allowed_domains())

        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('1', 'true', 'yes')

    @api.model
    def _mv_oauth_find_user(self, provider, validation):
        """Resolve the Odoo user this OAuth identity belongs to.

        Returns a single res.users record, or an empty recordset when
        the identity cannot be resolved safely.

        Every exit path logs under the [MV-OAUTH] marker so a failing
        sign-in can be diagnosed from the server log:
            grep MV-OAUTH odoo.log
        """
        Users = self.sudo()
        oauth_uid = validation.get('user_id')

        # Log what the provider actually returned. Never log the access
        # token or the raw payload - just the key names plus the two
        # claims we depend on.
        _logger.info(
            "[MV-OAUTH] provider=%s claims=%s email=%r email_verified=%r "
            "sub=%r",
            provider,
            sorted(validation.keys()),
            validation.get('email'),
            validation.get('email_verified',
                           validation.get('verified_email')),
            oauth_uid,
        )

        # --- 1. already linked ------------------------------------
        if oauth_uid:
            linked = Users.search([
                ('oauth_uid', '=', oauth_uid),
                ('oauth_provider_id', '=', provider),
            ], limit=2)
            if len(linked) == 1:
                _logger.info(
                    "[MV-OAUTH] matched already-linked user %s (id=%s).",
                    linked.login, linked.id,
                )
                return linked
            if len(linked) > 1:
                _logger.error(
                    "OAuth link: %s users share oauth_uid=%s on provider %s "
                    "- refusing to sign in. Clean up the duplicates.",
                    len(linked), oauth_uid, provider,
                )
                return Users.browse()

        # --- 2. fall back to verified email -----------------------
        if not self._mv_oauth_link_enabled():
            _logger.warning(
                "[MV-OAUTH] email linking is DISABLED "
                "(mv_auth_oauth.link_by_email=0) - cannot link.",
            )
            return Users.browse()

        email = (validation.get('email') or '').strip().lower()
        if not email:
            _logger.error(
                "[MV-OAUTH] provider %s returned NO email claim, so the "
                "existing user cannot be matched. Check the provider's "
                "Scope includes 'email' and its Validation Endpoint is "
                "https://www.googleapis.com/oauth2/v3/userinfo",
                provider,
            )
            return Users.browse()

        if not self._mv_oauth_email_is_verified(validation):
            _logger.error(
                "[MV-OAUTH] refusing to match %s - provider did not "
                "assert email_verified (got %r). If this provider never "
                "sends that claim, set mv_auth_oauth.trust_unverified_email=1 "
                "ONLY if you also set mv_auth_oauth.allowed_domains.",
                email,
                validation.get('email_verified',
                               validation.get('verified_email')),
            )
            return Users.browse()

        allowed = self._mv_oauth_allowed_domains()
        if allowed:
            domain_part = email.rsplit('@', 1)[-1]
            if domain_part not in allowed:
                _logger.warning(
                    "OAuth link: refusing %s - domain '%s' is not in "
                    "mv_auth_oauth.allowed_domains.", email, domain_part,
                )
                return Users.browse()

        # Resolution precedence: LOGIN beats EMAIL.
        #
        # `login` carries a unique constraint (res_users_login_key), so a
        # login hit identifies exactly one account and is the strongest
        # signal available. `email` is just a contact field - it is not
        # unique and is frequently duplicated, most often because the
        # `admin` account was given a real person's address. Treating
        # both as equal made that a fatal ambiguity; ranking them
        # resolves it without weakening the check, because we still
        # refuse when the CHOSEN tier is itself ambiguous.
        candidates = Users.search([
            ('login', '=ilike', email), ('active', '=', True),
        ], limit=3)
        if candidates:
            _logger.info(
                "[MV-OAUTH] matched on LOGIN: %s", candidates.mapped('login'),
            )
        else:
            candidates = Users.search([
                ('email', '=ilike', email), ('active', '=', True),
            ], limit=3)
            if candidates:
                _logger.info(
                    "[MV-OAUTH] no login match; matched on EMAIL: %s",
                    candidates.mapped('login'),
                )

        if not candidates:
            # Most common real cause: the Odoo login differs from the
            # Google address, or the user record is archived.
            archived = Users.with_context(active_test=False).search([
                '|', ('login', '=ilike', email), ('email', '=ilike', email),
            ], limit=3)
            if archived:
                _logger.error(
                    "[MV-OAUTH] %s matches user(s) %s but they are "
                    "ARCHIVED (active=False). Re-activate to allow login.",
                    email, archived.mapped('login'),
                )
            else:
                _logger.error(
                    "[MV-OAUTH] no Odoo user has login or email = %s. "
                    "The Google address must match the Odoo user's Login "
                    "or Email exactly.", email,
                )
            return Users.browse()
        if len(candidates) > 1:
            # Only reachable on the EMAIL tier - `login` is unique, so a
            # login match can never return more than one row.
            _logger.error(
                "[MV-OAUTH] %s active users share the email %s (%s) and "
                "none of them uses it as their Login - refusing to guess. "
                "Give exactly one of these users that address as their "
                "Login, or clear the Email field on the others.",
                len(candidates), email, candidates.mapped('login'),
            )
            return Users.browse()

        # Never silently re-point a user already bound to another
        # provider identity.
        user = candidates
        if user.oauth_uid and user.oauth_uid != oauth_uid:
            _logger.error(
                "OAuth link: user %s is already linked to a different "
                "oauth_uid - refusing to overwrite.", user.login,
            )
            return Users.browse()

        return user

    # ------------------------------------------------------------------
    # Override
    # ------------------------------------------------------------------
    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        # If this line is absent from the log during a sign-in attempt,
        # the override is NOT loaded - upgrade the module.
        _logger.info("[MV-OAUTH] override active, resolving sign-in...")
        user = self._mv_oauth_find_user(provider, validation)
        if not user:
            _logger.warning(
                "[MV-OAUTH] could not resolve a user; falling back to "
                "stock auth_oauth (which will deny access).",
            )
            # Could not resolve safely - let stock behaviour decide
            # (which will raise AccessDenied, or sign the user up if
            # signup is deliberately enabled).
            return super()._auth_oauth_signin(provider, validation, params)

        oauth_uid = validation.get('user_id')
        vals = {'oauth_access_token': params.get('access_token')}
        newly_linked = False
        if oauth_uid and user.oauth_uid != oauth_uid:
            vals['oauth_provider_id'] = provider
            vals['oauth_uid'] = oauth_uid
            newly_linked = True

        user.sudo().write(vals)

        if newly_linked:
            _logger.info(
                "OAuth link: bound Google identity %s to existing Odoo "
                "user %s (id=%s) via verified email %s.",
                oauth_uid, user.login, user.id,
                (validation.get('email') or '').strip().lower(),
            )
        return user.login
