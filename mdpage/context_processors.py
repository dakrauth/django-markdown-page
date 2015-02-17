from mdpage import utils

#-------------------------------------------------------------------------------
def mdpage(request):
    return {'mdpage': utils.mdpage_conf.context_conf}
    