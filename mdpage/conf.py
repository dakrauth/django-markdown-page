from collections import ChainMap
from functools import lru_cache
from django.conf import settings

DEFAULT_SETTINGS = {
    'listing_layout': 'list',
    'markdown_mdpage_re': r'\[\[([^]]+)\]\]',
    'markdown_table_classes': 'table table-striped table-bordered',
}

project_settings = getattr(settings, 'MARKDOWN_PAGE', {})
prefix_settings = project_settings.pop('prefixes', {})


@lru_cache(maxsize=None)
def get_settings(prefix=None):
    return ChainMap(prefix_settings.get(prefix, {}), project_settings, DEFAULT_SETTINGS)
