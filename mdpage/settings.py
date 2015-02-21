import re
from django.conf import settings

DEFAULT_SETTINGS = {
    'link_patterns':  [],
    'mdpage_re':  r'\[\[([^]]+)\]\]',
    'table_classes':  'table table-striped table-bordered',
    'link_classes':  '',
    'home_title':  'home',

    'extras': {
        'footnotes': True,
        'demote-headers': +1,
        'wiki-tables': True,
        'tables': True,
        'fenced-code-blocks': {}
    },

    'show_history_link': False,
    'show_recent_activity_link': False,
    'show_text_link': False,
    'show_topics': True,
}

mdpage_settings = dict(DEFAULT_SETTINGS.copy(), **getattr(settings, 'MARKDOWN_PAGE', {}))

def get_mdpage_setting(key, default=None):
    return mdpage_settings.get(key, default)

