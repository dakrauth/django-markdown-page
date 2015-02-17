from datetime import datetime
from django import forms
from django.contrib import messages
from mdpage import models


#===============================================================================
class MarkdownPageForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)

    #===========================================================================
    class Meta:
        model = models.MarkdownPage
        fields = ('title', 'status', 'text', 'tags')

    #---------------------------------------------------------------------------
    def clean(self):
        if (
            self.instance and 
            self.instance.locked and
            self.instance.locked < datetime.now()
        ):
            raise forms.ValidationError('Allotted time has expired.')
            
        return self.cleaned_data
        
    #---------------------------------------------------------------------------
    def save(self, request):
        if not self.has_changed():
            messages.warning(request, 'No changes saved')
        else:
            #import ipdb; ipdb.set_trace()
            instance = super(MarkdownPageForm, self).save(commit=False)
            instance.save(user=request.user)
            self.save_m2m()
            messages.info(request, 'Page saved')

        self.instance.unlock(request)
        return self.instance


#===============================================================================
class ContentForm(forms.ModelForm):
    
    #===========================================================================
    class Meta:
        model = models.StaticContent
        fields = ('label', 'description', 'media')
        
    #---------------------------------------------------------------------------
    def save(self, page):
        c = super(ContentForm, self).save(commit=False)
        c.page = page
        c.save()
        return c
        
