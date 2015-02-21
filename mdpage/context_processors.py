from mdpage.settings import mdpage_settings

context = {k: v for k,v in mdpage_settings.items() if k.startswith('show_')}


#-------------------------------------------------------------------------------
def mdpage(request):
    return {'mdpage': context}
    