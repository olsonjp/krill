from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Site View
class HomeView(View):
    template_name = 'home.html'

    def get(self, request):
        return render(request, self.template_name)


@method_decorator(login_required, name='dispatch')
class StorageView(View):
    template_name = 'storage/storage.html'

    def get(self, request):
        return render(request, self.template_name)
