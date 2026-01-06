# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website',
    'category': 'Website/Website',
    'sequence': 20,
    'summary': 'Enterprise website builder',
    'website': 'https://www.odoo.com/app/website',
    'version': '1.0',
    'depends': [
        'base',
        'digest',
        'web',
        'web_editor',
        'html_editor',
        'http_routing',
        'portal',
        'social_media',
        'auth_signup',
        'mail',
        'google_recaptcha',
        'utm',
    ],
    'external_dependencies': {
        'python': ['geoip2'],
    },
    'data': [
        # security.xml first, data.xml need the group to exist (checking it)
        'security/ir.model.access.csv',
        'views/website_visitor_views.xml',
    ],
    'demo': [
        'data/website_visitor_demo.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
