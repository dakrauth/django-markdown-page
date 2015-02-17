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
        'fenced-code-blocks': True
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
    
    _color_code_re =  re.compile(r'^(?::::|#!)([\w_+-]+)\s')
    extras = ['footnotes', 'link-patterns']

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
    def _do_link_patterns(self, text):
        text = super(MDPageMarkdown, self)._do_link_patterns(text)
        if self.make_mdpage_link:
            return mdpage_conf.mdpage_re.sub(self.mdpage_pattern_repl, text)
        else:
            return text
        
    #---------------------------------------------------------------------------
    def _code_block_sub(self, match):
        codeblock = self._outdent(match.group(1))
        codeblock = self._detab(codeblock).lstrip('\n').rstrip()

        m = self._color_code_re.match(codeblock)
        if not m:
            return "\n<pre><code>{}</code></pre>\n".format(self._encode_code(codeblock))

        junk, rest = codeblock.split('\n', 1)
        lexer = self._get_pygments_lexer(m.group(1))
        if lexer:
            codeblock = rest.lstrip("\n")   # Remove lexer declaration line.
            fmt_opts = self.extras['code-color'] or {}
            colored = self._color_with_pygments(codeblock, lexer, **fmt_opts)
            return "\n\n{}\n\n".format(colored)


#-------------------------------------------------------------------------------
def markdown(text, make_mdpage_link=None):
    mdww = MDPageMarkdown(
        make_mdpage_link,
        link_patterns=mdpage_conf.link_patterns,
        extras=mdpage_conf.extras
    )
    html = unicode(mdww.convert(text))
    if mdpage_conf.table_classes:
        html.replace('<table>', '<table class="{}">'.format(mdpage_conf.table_classes))

    return html

