# -*- coding: utf-8 -*-

from urllib.parse import quote
from odoo import models, api

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def get_authenticated_start_url(self):
        """
        Returns the survey open URL wrapped inside a login redirect URL.
        If the user is not logged in, Odoo will present the login screen first.
        Once authenticated, the smart route /survey/open/<access_token> routes:
        - Internal Users -> directly to internal survey fill form
        - Portal Users -> directly to /my/surveys portal menu
        """
        self.ensure_one()
        open_url = f'/survey/open/{self.access_token}'
        return f'/web/login?redirect={quote(open_url)}'
