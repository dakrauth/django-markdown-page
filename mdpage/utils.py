'''
'''
import re
import unicodedata
from markdown2 import Markdown
from django.contrib.auth.decorators import user_passes_test, login_required
from .settings import get_settings

superuser_required = user_passes_test(lambda u: u.is_authenticated() and u.is_active and u.is_superuser)
staff_required = user_passes_test(lambda u: u.is_authenticated() and u.is_active and u.is_staff)

#-------------------------------------------------------------------------------
def get_mdp_type_template_list(mdp_type, tmpl_part):
    return [
        'mdpage/types/{}/{}'.format(mdp_type.prefix or '__root__', tmpl_part),
        'mdpage/{}'.format(tmpl_part)
    ]


#-------------------------------------------------------------------------------
def slugify(value):
    value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)


#===============================================================================
class MDPageMarkdown(Markdown):
    
    #---------------------------------------------------------------------------
    def __init__(self, make_mdpage_link, settings, *args, **kws):
        super(MDPageMarkdown, self).__init__(*args, **kws)
        self.make_mdpage_link = make_mdpage_link
        self.mdpage_re = None
        self.settings = settings
        self.table_classes = settings.get('table_classes')
        if self.make_mdpage_link:
            regex = settings.get('mdpage_re')
            if regex:
                self.mdpage_re = re.compile(regex)
        
    #---------------------------------------------------------------------------
    def _mdpage_pattern_repl(self, match):
        title = match.group(1).strip()
        wcls = self.setting.get('link_classes')
        return '<a {}href="{}">{}</a>'.format(
            'class="{}" '.format(wcls) if wcls else '',
            self.make_mdpage_link(title),
            title
        )

    #---------------------------------------------------------------------------
    def _run_span_gamut(self, text):
        if self.make_mdpage_link and self.mdpage_re:
            text = self.mdpage_re.sub(self._mdpage_pattern_repl, text)
        
        return super(MDPageMarkdown, self)._run_span_gamut(text)

    #---------------------------------------------------------------------------
    def _do_table_classes(self, text):
        if self.table_classes:
            text = text.replace('<table>', '<table class="{}">'.format(self.table_classes))
        return text

    #---------------------------------------------------------------------------
    def _do_wiki_tables(self, text):
        text = super(MyMarkdown, self)._do_wiki_tables(text)
        return self._do_table_classes(text)

    #---------------------------------------------------------------------------
    def _do_tables(self, text):
        text = super(MyMarkdown, self)._do_tables(text)
        return self._do_table_classes(text)


#-------------------------------------------------------------------------------
def mdpage_markdown(text, make_mdpage_link=None, settings=None):
    settings = settings or get_settings()
    kwargs = {}
    if 'extras' in conf:
        kwargs['extras'] = conf['extras']
    
    if 'link_patterns' in conf:
        kwargs['link_patterns'] = conf['link_patterns']

    md = MDPageMarkdown(make_mdpage_link, settings, **kwargs)
    return unicode(md.convert(text))

