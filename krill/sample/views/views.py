from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import Sample, Aliquot, AliquotType, Source


def index(request):
    return HttpResponse('Hello, welcome to the index page.')


class SampleView(LoginRequiredMixin, View):
    template_name = 'sample/sample.html'

    def get(self, request):
        context = {
            'sample_count': Sample.objects.count(),
            'aliquot_count': Aliquot.objects.count(),
            'aliquot_type_count': AliquotType.objects.count(),
            'source_count': Source.objects.count(),
        }
        return render(request, self.template_name, context)
