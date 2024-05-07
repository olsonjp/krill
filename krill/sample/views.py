import re
from collections import namedtuple

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from sample.models import Sample

__all__ = (
    'SampleView',
)

class SampleView(View):
    template_name = 'sample/sample.html'

    samples = Sample.objects.all()
    print(samples)

    context = {
        'samples':samples
    }

    def get(self, request):
        return render(request, self.template_name, self.context)
