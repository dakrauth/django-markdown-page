from django import template
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
        html = utils.markdown(self.nodelist.render(context))
        return html


#-------------------------------------------------------------------------------
@register.filter(name='markdown')
def markdown(text):
    return mark_safe(utils.markdown(text))


#-------------------------------------------------------------------------------
@register.tag(name='markdown')
def do_markdown(parser, token):
    nodelist = parser.parse(('endmarkdown',))
    parser.delete_first_token()
    return MarkdownNode(nodelist)
    

