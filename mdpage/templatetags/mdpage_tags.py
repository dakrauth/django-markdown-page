from django import template
from django.template import loader
from django.utils.safestring import mark_safe
from mdpage import utils

register = template.Library()

#===============================================================================
class MarkdownNode(template.Node):

    #---------------------------------------------------------------------------
    def __init__(self, nodelist):
        self.nodelist = nodelist
        
    #---------------------------------------------------------------------------
    def render(self, context):
        html = utils.mdpage_markdown(self.nodelist.render(context))
        return html


#-------------------------------------------------------------------------------
@register.filter(name='markdown')
def markdown(text):
    return mark_safe(utils.mdpage_markdown(text))


#-------------------------------------------------------------------------------
@register.tag(name='markdown')
def do_markdown(parser, token):
    nodelist = parser.parse(('endmarkdown',))
    parser.delete_first_token()
    return MarkdownNode(nodelist)

#-------------------------------------------------------------------------------
@register.simple_tag
def select_template(mdp_type, tmpl_part):
    return loader.select_template(utils.get_mdp_type_template_list(mdp_type, tmpl_part))
