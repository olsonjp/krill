from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

class KrillLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('home') 