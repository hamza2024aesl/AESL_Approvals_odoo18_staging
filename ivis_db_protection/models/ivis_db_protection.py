from odoo.addons.web.controllers import database
import odoo
from lxml import html
from odoo.tools.misc import file_open
from odoo import http
from odoo.http import request
from odoo.addons.base.models.ir_qweb import render as qweb_render

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

from odoo import models, fields

class Database(database.Database):

    def _render_template(self, **d):
        d.setdefault('manage', True)
        d['insecure'] = odoo.tools.config.verify_admin_password('admin')
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        d['pattern'] = DBNAME_PATTERN

        # databases delete protection
        db_to_restrict_delete = odoo.tools.config.get('db_delete_restrict', False)
        if db_to_restrict_delete:
            databases_restrict_delete = db_to_restrict_delete.replace(" ", "")
            if db_to_restrict_delete.lower() != 'all':
                d['delete_restrict'] = databases_restrict_delete.split(',')
        else:
            d['delete_restrict'] = [None]

        # databases duplicate protection
        db_to_restrict_duplicate = odoo.tools.config.get('db_duplicate_restrict', False)
        if db_to_restrict_duplicate:
            databases_restrict_duplicate = db_to_restrict_duplicate.replace(" ", "")
            if databases_restrict_duplicate.lower() != 'all':
                d['duplicate_restrict'] = databases_restrict_duplicate.split(',')
        else:
            d['duplicate_restrict'] = [None]

        # databases backup protection
        db_to_restrict_backup = odoo.tools.config.get('db_backup_restrict', False)
        if db_to_restrict_backup:
            databases_restrict_backup = db_to_restrict_backup.replace(" ", "")
            if databases_restrict_backup.lower() != 'all':
                d['backup_restrict'] = databases_restrict_backup.split(',')
        else:
            d['backup_restrict'] = [None]

        # databases list
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = odoo.service.db.list_db_incompatible(
                d['databases'])
        except odoo.exceptions.AccessDenied:
            d['databases'] = [request.db] if request.db else []

        templates = {}

        with file_open(
                "ivis_db_protection/views/database_manager.html",
                "r") as fd:
            templates['database_manager'] = fd.read()
        with file_open(
                "web/static/src/public/database_manager.master_input.qweb.html",
                "r") as fd:
            templates['master_input'] = fd.read()
        with file_open(
                "web/static/src/public/database_manager.create_form.qweb.html",
                "r") as fd:
            templates['create_form'] = fd.read()

        def load(template_name):
            fromstring = html.document_fromstring if template_name == 'database_manager' else html.fragment_fromstring
            return (fromstring(templates[template_name]), template_name)

        return qweb_render('database_manager', d, load)