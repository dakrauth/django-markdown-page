from django import forms
from django.utils import timezone
from django.contrib import messages
from django.forms.models import modelformset_factory

from . import models


class TagForm(forms.ModelForm):

    class Meta:
        model = models.MarkdownPage
        fields = ('tags',)


TagsFormset = modelformset_factory(models.MarkdownPage, form=TagForm)


class MarkdownPageForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)
    timestamp = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = models.MarkdownPage
        fields = ('title', 'status', 'text', 'tags', 'timestamp')

    def __init__(self, initial=None, instance=None, **kwargs):
        self.request = kwargs.pop('request')
        self.mdp_type = kwargs.pop('mdp_type')
        initial['timestamp'] = instance.updated.isoformat() if instance else 'N/A'
        super().__init__(initial=initial, instance=instance, **kwargs)

    def save(self):
        if not self.has_changed():
            messages.warning(self.request, 'No changes saved')
        else:
            instance = super(MarkdownPageForm, self).save(commit=False)
            if not instance.pk:
                instance.type = self.mdp_type
            instance.save(user=self.request.user)
            self.save_m2m()
            messages.success(self.request, 'Page saved')

        return self.instance


class ContentForm(forms.ModelForm):

    class Meta:
        model = models.StaticContent
        fields = ('label', 'description', 'media')

    def save(self, page):
        c = super(ContentForm, self).save(commit=False)
        c.page = page
        c.save()
        return c

