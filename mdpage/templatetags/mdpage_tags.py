from django import template
from django.template import loader
from mdpage import utils

register = template.Library()


class MarkdownNode(template.Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        page = context.get('page')
        return utils.mdpage_markdown(
            self.nodelist.render(context),
            page.type if page else None
        )


@register.tag(name='markdown')
def do_markdown(parser, token):
    nodelist = parser.parse(('endmarkdown',))
    parser.delete_first_token()
    return MarkdownNode(nodelist)


@register.simple_tag
def select_template(mdp_type, tmpl_part):
    if not isinstance(mdp_type, str):
        mdp_type = mdp_type.prefix

    return loader.select_template(
        utils.get_mdp_type_template_list(tmpl_part, mdp_type)
    )
