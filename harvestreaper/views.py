from django.views.generic import TemplateView
from django.shortcuts import redirect
from datetime import datetime, timedelta

from harvestreaper.googlecal.utils import get_calendar_events
from harvestreaper.harvest.models import HarvestToken
from harvestreaper.harvest.utils import get_harvest_account


class HomePageView(TemplateView):
    template_name = 'home.html'

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user

        if user.is_authenticated:
            google_social_account = None
            if hasattr(self.request.user, 'socialaccount_set'):
                google_social_account = self.request.user.socialaccount_set.filter(
                    provider="googlecal").first()
            harvest_token = HarvestToken.objects.filter(user=self.request.user).first()

            # Get a harvest token if necessary
            if not harvest_token:
                return redirect('harvest_auth')

            # Make sure the token isn't expired for harvest
            if harvest_token.is_expired:
                harvest_token.refresh()

            kwargs['google'] = google_social_account
            kwargs['harvest'] = harvest_token

        return super(HomePageView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        google_social_account = kwargs.pop('google', None)
        harvest_token = kwargs.pop('harvest', None)

        # Only show import data if there are both valid tokens
        if google_social_account and harvest_token:
            token = google_social_account.socialtoken_set.first()

            # Google
            now = datetime.utcnow()
            # We add and subtract here to account for zero indexing and bring things
            # back to previous Sat.
            # Adding 4 to account for UTC
            start_day = now - timedelta(days=now.weekday() + 2) - \
                timedelta(hours=now.hour - 4, minutes=now.minute)
            end_day = now + timedelta(days=5 - now.weekday()) - \
                timedelta(hours=now.hour - 4, minutes=now.minute)
            massaged_events = get_calendar_events(token, start_day, end_day)
            context['upcoming_events'] = massaged_events
            context['time_window'] = {
                'start': start_day.strftime('%a, %d %b %Y'),
                'end': end_day.strftime('%a, %d %b %Y')
            }

            # Harvest
            account = get_harvest_account(harvest_token)
            context['harvest_account_id'] = account
        return context
