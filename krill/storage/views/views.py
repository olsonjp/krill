from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Site View
class HomeView(View):
    template_name = 'home.html'

    def get(self, request):
        """
        if settings.LOGIN_REQUIRED and not request.user.is_authenticated:
            return redirect('login')

        # Construct the user's custom dashboard layout
        try:
            dashboard = get_dashboard(request.user).get_layout()
        except Exception:
            messages.error(request, _(
                "There was an error loading the dashboard configuration. A default dashboard is in use."
            ))
            dashboard = get_default_dashboard(config=DEFAULT_DASHBOARD).get_layout()

        # Check whether a new release is available. (Only for staff/superusers.)
        new_release = None
        if request.user.is_staff or request.user.is_superuser:
            latest_release = cache.get('latest_release')
            if latest_release:
                release_version, release_url = latest_release
                if release_version > version.parse(settings.VERSION):
                    new_release = {
                        'version': str(release_version),
                        'url': release_url,
                    } """

        return render(request, self.template_name)
        """, {
        'dashboard': dashboard,
        'new_release': new_release,
        })"""


@method_decorator(login_required, name='dispatch')
class StorageView(View):
    template_name = 'storage/storage.html'

    def get(self, request):
        """
        if settings.LOGIN_REQUIRED and not request.user.is_authenticated:
            return redirect('login')

        # Construct the user's custom dashboard layout
        try:
            dashboard = get_dashboard(request.user).get_layout()
        except Exception:
            messages.error(request, _(
                "There was an error loading the dashboard configuration. A default dashboard is in use."
            ))
            dashboard = get_default_dashboard(config=DEFAULT_DASHBOARD).get_layout()

        # Check whether a new release is available. (Only for staff/superusers.)
        new_release = None
        if request.user.is_staff or request.user.is_superuser:
            latest_release = cache.get('latest_release')
            if latest_release:
                release_version, release_url = latest_release
                if release_version > version.parse(settings.VERSION):
                    new_release = {
                        'version': str(release_version),
                        'url': release_url,
                    } """

        return render(request, self.template_name)