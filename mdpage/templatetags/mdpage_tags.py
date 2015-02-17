from django import template
from django.utils.safestring import mark_safe
from mdpage import utils
register = template.Library()

#-------------------------------------------------------------------------------
@register.filter(name='markdown')
def markdown(text):
    return mark_safe(utils.markdown(text))
