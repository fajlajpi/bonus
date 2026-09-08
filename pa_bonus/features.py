"""
Per-deployment feature flags.

Not every country runs every part of the programme: Poland, for instance, has
no Extra Goals and does not use the SMS export. Rather than maintaining a
branch per market, each deployment switches features on or off through its own
settings.ini / .env, and the codebase stays identical everywhere.

A disabled feature is hidden from every audience - clients, sales reps and
managers alike - so that nobody has to reason about a feature their market does
not use. Enforcement has three layers:

  1. settings.FEATURES        - the source of truth, one entry per feature.
  2. feature_required /       - guard views so a disabled feature is
     FeatureRequiredMixin       unreachable even by typing the URL.
  3. the `features` context   - hide the links and panels that lead there.
     processor

URLs stay registered even when a feature is off. Dropping them from urlpatterns
would turn any {% url %} tag that was missed when hiding a link into a
NoReverseMatch, breaking the whole page; a guarded view turns the same mistake
into a 404 on a page nobody links to.
"""
from functools import wraps

from django.conf import settings
from django.http import Http404


def feature_enabled(name):
    """
    Return True if the named feature is enabled for this deployment.

    Unknown names return False: a feature nobody has declared is one this
    deployment does not have.
    """
    return bool(settings.FEATURES.get(name, False))


def feature_required(name):
    """
    Restrict a function-based view to deployments where `name` is enabled.

    Raises Http404 when disabled, so a switched-off feature is indistinguishable
    from a URL that was never there.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not feature_enabled(name):
                raise Http404(f"Feature '{name}' is not enabled for this deployment.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


class FeatureRequiredMixin:
    """
    Restrict a class-based view to deployments where `feature_name` is enabled.

    Mix in ahead of the view class, alongside whatever access-control mixin the
    view already uses:

        class GoalsOverviewView(ManagerGroupRequiredMixin, FeatureRequiredMixin, ListView):
            feature_name = 'extra_goals'
    """

    feature_name = None

    def dispatch(self, request, *args, **kwargs):
        if self.feature_name is None:
            raise ValueError(
                f"{type(self).__name__} uses FeatureRequiredMixin but does not "
                f"set feature_name."
            )
        if not feature_enabled(self.feature_name):
            raise Http404(f"Feature '{self.feature_name}' is not enabled for this deployment.")
        return super().dispatch(request, *args, **kwargs)
