# -*- coding: utf-8 -*-

{
    "name": "Prodo User Portal",
    "author": "PRODO",
    "website": "https://www.prodo.pk",
    "support": "info@prodo.pk",
    "category": "User",
    "summary": "User Portal",
    "description": """User Portal""",
    "version": "18.0",
    "depends": ['portal'],
    "data": [
        'views/appraisal_template.xml',
    ],
    "assets": {
        "web.assets_frontend": [
            '/prodo_user_portal/static/src/js/events.js',
            '/prodo_user_portal/static/src/js/appraisal.js',
        ],
    },
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}
