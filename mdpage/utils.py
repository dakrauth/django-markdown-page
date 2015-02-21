'''
'''
import re
import unicodedata
from django.conf import settings
from markdown2 import Markdown
from django.contrib.auth.decorators import user_passes_test, login_required
from .settings import get_mdpage_setting, mdpage_settings

superuser_required = user_passes_test(lambda u: u.is_authenticated() and u.is_active and u.is_superuser)
staff_required = user_passes_test(lambda u: u.is_authenticated() and u.is_active and u.is_staff)


#-------------------------------------------------------------------------------
def slugify(value):
    value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)


#===============================================================================
class MDPageMarkdown(Markdown):
    
    #---------------------------------------------------------------------------
    def __init__(self, make_mdpage_link, *args, **kws):
        super(MDPageMarkdown, self).__init__(*args, **kws)
        self.make_mdpage_link = make_mdpage_link
        self.mdpage_re = None
        if self.make_mdpage_link:
            regex = get_mdpage_setting('mdpage_re')
            if regex:
                self.mdpage_re = re.compile(regex)
        
    #---------------------------------------------------------------------------
    def mdpage_pattern_repl(self, match):
        title = match.group(1).strip()
        wcls = get_mdpage_setting('link_classes')
        return '<a {}href="{}">{}</a>'.format(
            'class="{}" '.format(wcls) if wcls else '',
            self.make_mdpage_link(title),
            title
        )

    #---------------------------------------------------------------------------
    def _run_span_gamut(self, text):
        if self.make_mdpage_link and self.mdpage_re:
            text = self.mdpage_re.sub(self.mdpage_pattern_repl, text)
        
        return super(MDPageMarkdown, self)._run_span_gamut(text)


#-------------------------------------------------------------------------------
def mdpage_markdown(text, make_mdpage_link=None, conf=None):
    conf = conf or mdpage_settings
    kwargs = {}
    if conf['extras']:
        kwargs['extras'] = conf['extras']
    
    if conf['link_patterns']:
        kwargs['link_patterns'] = conf['link_patterns']
        
    md = MDPageMarkdown(make_mdpage_link, **kwargs)
    html = unicode(md.convert(text))
    table_classes = conf.get('table_classes')
    if table_classes:
        html = html.replace('<table>', '<table class="{}">'.format(table_classes))

    return html

