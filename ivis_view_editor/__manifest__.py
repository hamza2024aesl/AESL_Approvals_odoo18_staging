# Copyright 2015-2020 Onestein (<https://www.onestein.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "BI View Editor",
    "summary": "Graphical BI views builder for Odoo",
    "images": ["static/description/main_screenshot.png"],
    "author": "Onestein,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/reporting-engine",
    "category": "Productivity",
    "version": "18.0",
    "development_status": "Beta",
    "depends": [
        "web", "spreadsheet_dashboard"
    ],
    "external_dependencies": {
        "deb": ["graphviz"],
        "python": ["pydot"],
    },
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/bve_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # "ivis_view_editor/static/src/components/**/*",
            "ivis_view_editor/static/src/components/ivis_view_editor/ivis_view_editor.css",
            "ivis_view_editor/static/src/components/ivis_view_editor/ivis_view_editor.esm.js",
            "ivis_view_editor/static/src/components/ivis_view_editor/ivis_view_editor.xml",
            "ivis_view_editor/static/src/components/ivis_view_editor/field_list.esm.js",
            "ivis_view_editor/static/src/components/ivis_view_editor/field_list.xml",
            "ivis_view_editor/static/src/components/ivis_view_editor/join_node_dialog.esm.js",
            "ivis_view_editor/static/src/components/ivis_view_editor/join_node_dialog.xml",
            "ivis_view_editor/static/src/components/ivis_view_editor/model_list.esm.js",
            "ivis_view_editor/static/src/components/ivis_view_editor/model_list.xml",
        ],
    },
    "uninstall_hook": "uninstall_hook",
}
