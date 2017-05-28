import re
from copy import deepcopy
from django.conf import settings

DEFAULT_SETTINGS = {
    'mdpage_re':  r'\[\[([^]]+)\]\]',
    'table_classes':  'table table-striped table-bordered',
    'home_slug':  'home',
    'home_layout': 'list',
    
    'extras': {
        'footnotes': True,
        'demote-headers': +1,
        'wiki-tables': True,
        'tables': True,
        'fenced-code-blocks': {}
    },
}

mdpage_settings = dict(DEFAULT_SETTINGS.copy(), **getattr(settings, 'MARKDOWN_PAGE', {}))
mdpage_type_settings = mdpage_settings.pop('types', {})


#-------------------------------------------------------------------------------
def dict_merge(a, b):
    if not isinstance(b, dict):
        return b
    
    result = deepcopy(a)
    for k, v in b.items():
        if k in result and isinstance(result[k], dict):
            result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


type_settings_cache = None

#-------------------------------------------------------------------------------
def get_settings(prefix=None):
    global type_settings_cache
    if type_settings_cache is None:
        type_settings_cache = {None: mdpage_settings}
        for type_prefix, type_settings in mdpage_type_settings.items():
            type_settings_cache[type_prefix] = (
                dict_merge(mdpage_settings, type_settings)
                if type_settings
                else mdpage_settings
            )
        
    return type_settings_cache.get(prefix, mdpage_settings)

