'''
'''
import re
import unicodedata
from django.conf import settings
from markdown2 import Markdown

#-------------------------------------------------------------------------------
def slugify(value):
    value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)


#===============================================================================
class MDPageConf(object):

    link_patterns       = []
    mdpage_re             = r'\[\[([^]]+)\]\]'
    title_splitter      = r'[^\w_-]+'
    table_classes       = 'table table-striped table-bordered'
    mdpage_link_classes   = ''
    read_login_required = False
    home_title          = 'home'
    extras = {
        'footnotes': True,
        'demote-headers': +1,
        'wiki-tables': True,
        'tables': True,
        'fenced-code-blocks': {}
    }
    context_conf = {
        'show_history_link': False,
        'show_text_link': False,
        'show_tags': True
    }

    #---------------------------------------------------------------------------
    def __init__(self, kws):
        self.__dict__.update(kws)
        self.mdpage_re = re.compile(self.mdpage_re)
        self.title_splitter = re.compile(self.title_splitter).split


mdpage_conf = MDPageConf(getattr(settings, 'MARKDOWN_PAGE', {}))


#===============================================================================
class MDPageMarkdown(Markdown):
    
    #---------------------------------------------------------------------------
    def __init__(self, make_mdpage_link, *args, **kws):
        super(MDPageMarkdown, self).__init__(*args, **kws)
        self.make_mdpage_link = make_mdpage_link
        
    #---------------------------------------------------------------------------
    def mdpage_pattern_repl(self, match):
        title = match.group(1).strip()
        wcls = mdpage_conf.mdpage_link_classes
        return '<a {}href="{}">{}</a>'.format(
            'class="{}" '.format(wcls) if wcls else '',
            self.make_mdpage_link(title),
            title
        )

    #---------------------------------------------------------------------------
    def _run_span_gamut(self, text):
        if self.make_mdpage_link:
            text = mdpage_conf.mdpage_re.sub(self.mdpage_pattern_repl, text)
        
        return super(MDPageMarkdown, self)._run_span_gamut(text)


#-------------------------------------------------------------------------------
def markdown(text, make_mdpage_link=None):
    md = MDPageMarkdown(
        make_mdpage_link,
        link_patterns=mdpage_conf.link_patterns,
        extras=mdpage_conf.extras
    )
    html = unicode(md.convert(text))
    if mdpage_conf.table_classes:
        html = html.replace('<table>', '<table class="{}">'.format(mdpage_conf.table_classes))

    return html

