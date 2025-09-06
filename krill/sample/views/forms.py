from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib import messages
from django.urls import reverse
from ..forms import (
    SampleForm,
    AliquotForm, AliquotLocationForm, AliquotTypeForm,
    AliquotDispositionForm,
)

class SampleFormView(View):
    template_name = 'forms/model_form.html'
    success_url = 'sample:list'
    def get_form_class(self):
        form_types = {
            'sample': SampleForm,
            'aliquot': AliquotForm,
            'aliquot-location': AliquotLocationForm,
            'aliquot-type': AliquotTypeForm,
            'aliquot-disposition': AliquotDispositionForm,
        }
        return form_types.get(self.kwargs.get('type'))
    def get_success_url(self):
        return reverse(self.success_url)
    def get_title(self):
        titles = {
            'sample': 'New Sample',
            'aliquot': 'New Aliquot',
            'aliquot-location': 'New Aliquot Location',
            'aliquot-type': 'New Aliquot Type',
            'aliquot-disposition': 'New Disposition',
        }
        return titles.get(self.kwargs.get('type'), 'New Item')
    def get_description(self):
        descriptions = {
            'sample': 'Create a new sample',
            'aliquot': 'Create a new aliquot from a sample',
            'aliquot-location': 'Assign an aliquot to a storage location',
            'aliquot-type': 'Define a new type of aliquot',
            'aliquot-disposition': 'Define a new disposition status',
        }
        return descriptions.get(self.kwargs.get('type'), '')

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        if not form_class:
            messages.error(request, 'Invalid form type')
            return redirect(self.get_success_url())
        form = form_class()
        context = {
            'form': form,
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
