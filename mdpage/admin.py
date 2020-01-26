from django.contrib import admin
from . import models as mdpage

# The following classes define the admin interface for your models.
# See http://docs.djangoproject.com/en/dev/ref/contrib/admin/ for
# a full list of the options you can use in these classes.


@admin.register(mdpage.MarkdownPage)
class MarkdownPageAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'type',
        'status',
        'created',
        'updated',
    )
    search_fields = ('title', 'source')
    list_filter = ('type', 'status')
    # ordering = ('',)


@admin.register(mdpage.MarkdownPageArchive)
class MarkdownPageArchiveAdmin(admin.ModelAdmin):
    list_display = (
        'page_title',
        'page_type',
        'created',
    )

    def page_title(self, obj):
        return obj.page.title

    def page_type(self, obj):
        return obj.page.type


@admin.register(mdpage.StaticContent)
class StaticContentAdmin(admin.ModelAdmin):
    list_display = (
        'label',
        'description',
        'type',
        'subtype',
        'created',
        'updated',
    )


@admin.register(mdpage.MarkdownPageType)
class MarkdownPageTypeAdmin(admin.ModelAdmin):
    list_display = (
        'prefix', 
        'description', 
        'created', 
        'updated', 
        'pub_date', 
        'end_date', 
        'status', 
    )
