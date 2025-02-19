from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib import messages
from django.urls import reverse
from ..forms import DeviceForm, ShelfForm, RackForm, BoxForm, SiteForm

class StorageFormView(View):
    template_name = 'forms/model_form.html'
    success_url = 'storage:list'
    
    def get_form_class(self):
        storage_type = self.kwargs.get('type')
        form_classes = {
            'site': SiteForm,
            'device': DeviceForm,
            'shelf': ShelfForm,
            'rack': RackForm,
            'box': BoxForm,
        }
        return form_classes.get(storage_type)
    
    def get_success_url(self):
        return reverse(self.success_url)

    def get_title(self):
        storage_type = self.kwargs.get('type').title()
        return f'Add New {storage_type}'
    
    def get_description(self):
        storage_type = self.kwargs.get('type').title()
        return f'Create a new {storage_type.lower()} in the storage system'

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        if not form_class:
            messages.error(request, 'Invalid storage type')
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
            messages.error(request, 'Invalid storage type')
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