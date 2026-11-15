from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.utils.translation import gettext as _

from netbox.plugins import get_plugin_config

from .choices import BranchStatusChoices
from .constants import COOKIE_NAME, EXEMPT_PATHS, QUERY_PARAM
from .utilities import BranchNotReady, get_active_branch, is_api_request

__all__ = ('BranchMiddleware',)

# A branch in one of these statuses becomes usable again without anyone acting on it: NEW is
# waiting for its provisioning job, the rest are running a job. Any other status that is not
# READY (merged, archived, failed, pending-migrations) needs an operator, or is final.
RETRYABLE_STATUSES = (BranchStatusChoices.NEW, *BranchStatusChoices.TRANSITIONAL)


def branch_not_ready_response(status):
    """
    The response to an API request which selects a branch that is not ready.

    A client such as an ingestion pipeline needs to know whether to wait or to give up, so a
    transitional status answers 503 with Retry-After and any other status 409. Like the 400 it
    replaces, the body is a static message: this runs ahead of REST API authentication, so the
    branch's name and status are not reported (see #672).
    """
    retryable = status in RETRYABLE_STATUSES
    response = JsonResponse(
        {'detail': _('Selected branch is not ready.'), 'retryable': retryable},
        status=503 if retryable else 409,
    )
    if retryable:
        response['Retry-After'] = str(get_plugin_config('netbox_branching', 'unavailable_retry_after'))
    return response


def discard_request_body(request):
    """
    Read and drop the request body of a request refused without running its view.

    A response sent while the body is still unread leaves those bytes on a keep-alive connection
    under some application servers (granian, which NetBox ships with): the next request the client
    sends on that connection then never completes. A client which retries a 503 on the same
    connection, as it should, hangs until its own timeout. Draining the body keeps the connection
    usable. Errors (e.g. the client went away) are ignored: the refusal is sent regardless.
    """
    try:
        while request.read(64 * 1024):
            pass
    except Exception:  # noqa: S110
        pass


class BranchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _apply_branch_cookie(self, response, branch, branch_change):
        """
        Apply or remove the branch cookie on the given response.

        Cookie attributes mirror Django's SESSION_COOKIE_* settings so the
        branch cookie is treated consistently with the session cookie by the
        browser (in particular, SameSite must be set explicitly — browsers
        that don't default to Lax will otherwise drop the cookie on
        cross-site navigation, causing branch writes to leak to main).
        """
        if branch:
            response.set_cookie(
                COOKIE_NAME,
                branch.schema_id,
                domain=settings.SESSION_COOKIE_DOMAIN,
                path=settings.SESSION_COOKIE_PATH,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        elif branch_change:
            response.delete_cookie(
                COOKIE_NAME,
                domain=settings.SESSION_COOKIE_DOMAIN,
                path=settings.SESSION_COOKIE_PATH,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )

    def __call__(self, request):

        # Skip branch activation for exempt paths
        if request.path in EXEMPT_PATHS:
            return self.get_response(request)

        # Set/clear the active Branch on the request
        try:
            branch = get_active_branch(request)
        except ObjectDoesNotExist:
            discard_request_body(request)
            return HttpResponseBadRequest('Invalid branch identifier')
        except BranchNotReady as e:
            discard_request_body(request)
            if is_api_request(request):
                return branch_not_ready_response(e.status)
            return HttpResponseBadRequest(_('Selected branch is not ready.'))
        request.active_branch = branch

        response = self.get_response(request)

        # Set/clear the branch cookie (for non-API requests)
        if not is_api_request(request):
            # Check if a branch is being activated/deactivated, or if a stale
            # cookie exists (cookie present but branch not active — e.g. branch
            # was archived or merged since the cookie was set).
            branch_change = QUERY_PARAM in request.GET or (COOKIE_NAME in request.COOKIES and not branch)

            # Redirect to dashboard if branch activation/deactivation results in 404
            if branch_change and response.status_code == 404:
                # Construct a more informative error message
                branch_name = f"branch '{branch.name}'" if branch else 'main'
                requested_url = request.path
                messages.warning(
                    request,
                    _('The requested object at {url} does not exist in {branch_name}.').format(
                        url=requested_url, branch_name=branch_name
                    ),
                )

                # Create redirect response and apply cookie operations to it
                redirect_response = HttpResponseRedirect('/')
                self._apply_branch_cookie(redirect_response, branch, branch_change)
                return redirect_response

            # Set/clear cookie on the normal response
            self._apply_branch_cookie(response, branch, branch_change)

        return response
