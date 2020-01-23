import re
import unicodedata

from .markdown import mdpage_markdown


def get_mdp_type_template_list(base_part, mdp_prefix=None):
    template_list = ['mdpage/{}'.format(base_part)]
    if mdp_prefix:
        template_list.insert(0, 'mdpage/{}/{}'.format(mdp_prefix, base_part))

    return template_list


def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = re.sub('[^\w\s-]', '', value.decode()).strip().lower()
    return re.sub('[-\s]+', '-', value)


