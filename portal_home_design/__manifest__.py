{
    'name': 'Portal Home Design',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Groups and restyles the portal home menu tiles (frontend only)',
    'depends': ['portal'],
    'data': [],
    'assets': {
        'web.assets_frontend': [
            'portal_home_design/static/src/css/portal_home.css',
            'portal_home_design/static/src/js/portal_home.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
