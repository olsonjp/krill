from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib import messages
from django.urls import reverse
from ..forms import (
    SampleForm,
    AliquotForm, AliquotTypeForm,
    AliquotDispositionForm,
)

class SampleFormView(View):
    template_name = 'forms/model_form.html'
    success_url = 'sample:list'
    
    def get_form_class(self):
        form_type = self.kwargs.get('type')
        form_classes = {
            'sample': SampleForm,
            'aliquot': AliquotForm,
            'aliquot-type': AliquotTypeForm,
            'aliquot-disposition': AliquotDispositionForm,
        }
        return form_classes.get(form_type)
    
    def get_success_url(self):
        return reverse(self.success_url)
    
    def get_title(self):
        form_type = self.kwargs.get('type').replace('-', ' ').title()
        return f'Add New {form_type}'
    
    def get_description(self):
        form_type = self.kwargs.get('type').replace('-', ' ').title()
        return f'Create a new {form_type.lower()} in the system'

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        if not form_class:
            messages.error(request, 'Invalid form type')
            return redirect(self.get_success_url())
            
        context = {
            'form': form_class(),
            'form_title': self.get_title(),
            'form_description': self.get_description(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        if not form_class:
            messages.error(request, 'Invalid form type')
            return redirect(self.get_success_url())
            
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'{self.get_title()} created successfully!')
            return redirect(self.get_success_url())
        
        context = {
            'form': form,
            'form_title': self.get_title(),
            'form_description': self.get_description(),
        }
        return render(request, self.template_name, context) 