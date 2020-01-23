import re
from markdown2 import Markdown

from ..conf import get_settings


class MDPageMarkdown(Markdown):

    def __init__(self, settings):
        super(MDPageMarkdown, self).__init__()

        self.table_classes = settings.get('table_classes', '')
        self.link_classes = settings.get('link_classes', '')
        self.make_mdpage_link = settings.get('mdpage_link', False)
        self.mdpage_re = None
        if self.make_mdpage_link:
            regex = settings.get('mdpage_re')
            if regex:
                self.mdpage_re = re.compile(regex)

    def _mdpage_pattern_repl(self, match):
        title = match.group(1).strip()
        return '<a {}href="{}">{}</a>'.format(
            'class="{}" '.format(self.link_classes),
            self.make_mdpage_link(title),
            title
        )

    def _run_span_gamut(self, text):
        if self.make_mdpage_link and self.mdpage_re:
            text = self.mdpage_re.sub(self._mdpage_pattern_repl, text)

        return super(MDPageMarkdown, self)._run_span_gamut(text)

    def _do_table_classes(self, text):
        if self.table_classes:
            text = text.replace('<table>', '<table class="{}">'.format(self.table_classes))
        return text

    def _do_wiki_tables(self, text):
        text = super(MDPageMarkdown, self)._do_wiki_tables(text)
        return self._do_table_classes(text)

    def _do_tables(self, text):
        text = super(MDPageMarkdown, self)._do_tables(text)
        return self._do_table_classes(text)


def mdpage_markdown(text, mdp_type=None):
    settings = get_settings(mdp_type.prefix if mdp_type else None)
    return MDPageMarkdown({
        k.replace('markdown_', '', 1): v for k, v in settings.items()
        if k.startswith('markdown_')
    }).convert(text)

