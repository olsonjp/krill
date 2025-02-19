from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import View

def index(request):
    return HttpResponse('Hello, welcome to the index page.')

class SampleView(View):
    template_name = 'sample/sample.html'

    def get(self, request):
        return render(request, self.template_name)