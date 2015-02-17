from django.contrib import admin
from mdpage import models as mdpage

# The following classes define the admin interface for your models.
# See http://docs.djangoproject.com/en/dev/ref/contrib/admin/ for
# a full list of the options you can use in these classes.

#===============================================================================
class MarkdownPageAdmin(admin.ModelAdmin):
    list_display = ( 
        'title',
        'version',
        'created',
        'updated',
    )
    search_fields = ('title', 'source')
    # list_filter = ('',)
    # ordering = ('',)



#===============================================================================
class MarkdownPageArchiveAdmin(admin.ModelAdmin):
    list_display = ( 
        'page',
        'version',
        'created',
    )
    # search_fields = ('',)
    # list_filter = ('',)
    # ordering = ('',)



#===============================================================================
class StaticContentAdmin(admin.ModelAdmin):
    list_display = ( 
        'label',
        'description',
        'type',
        'subtype',
        'created',
        'updated',
    )
    # search_fields = ('',)
    # list_filter = ('',)
    # ordering = ('',)



# Each of these lines registers the admin interface for one model. If
# you don't want the admin interface for a particular model, remove
# the line which registers it.
admin.site.register(mdpage.MarkdownPage, MarkdownPageAdmin)
admin.site.register(mdpage.MarkdownPageArchive, MarkdownPageArchiveAdmin)
admin.site.register(mdpage.StaticContent, StaticContentAdmin)


