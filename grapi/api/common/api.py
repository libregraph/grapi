"""Falcon customized implementation of API."""
import importlib
from functools import partial

from falcon import COMBINED_METHODS, routing

try:  # falcon 2.0+
    from falcon import APP as FalconAPI
    FALCON_VERSION = 2
except ImportError:  # falcon 1.0
    from falcon import API as FalconAPI
    FALCON_VERSION = 1


def map_http_methods(resource, suffix=None, suffix_method_caller=None):
    """Maps HTTP methods (e.g., GET, POST) to methods of a resource object.

    .. note:: This is Falcon2 ported code with some customization on introducing `*_suffix` methods.
        We check to ensure that if a resource doesn't have a `*_suffix` method, then we add it into
        the resource class on the fly. For instance, we have suffix="me" in routes, this function adds
        on_get_me, on_post_me, on_patch_me, an ... methods to the related resource class.

    :param resource: An object with *responder* methods, following the naming
        convention *on_\\**, that correspond to each method the resource
        supports. For example, if a resource supports GET and POST, it
        should define ``on_get(self, req, resp)`` and
        ``on_post(self, req, resp)``.
    :type resource: Resource
    :param suffix: Optional responder name suffix for this route. If
        a suffix is provided, Falcon will map GET requests to
        ``on_get_{suffix}()``, POST requests to ``on_post_{suffix}()``,
        etc, defaults to None.
    :type suffix: str, optional
    :param suffix_method_caller: replacement function for a suffix method, defaults to None.
    :type suffix_method_caller: Callable, optional

    :return: A mapping of HTTP methods to explicitly defined resource responders.
    :rtype: dict
    """
    method_map = {}

    for method in COMBINED_METHODS:
        try:
            responder_name = 'on_' + method.lower()
            if suffix:
                responder_name += '_' + suffix

                if not hasattr(resource, responder_name) and suffix_method_caller:
                    setattr(
                        resource, responder_name, partial(suffix_method_caller, responder_name)
                    )

            responder = getattr(resource, responder_name)
        except AttributeError:
            # resource does not implement this method
            pass
        else:
            # Usually expect a method, but any callable will do
            if callable(responder):
                method_map[method] = responder

    return method_map


class API(FalconAPI):
    """Customized API class based on Falcon's API."""

    _suffix_method_caller = None

    def set_suffix_method_caller(self, fn):
        """Set suffix method caller.

        :param fn: replacement function for suffix method patcher.
        :type fn: Callable

        :raises ValueError: when the function is not callable.
        :raises NameError: when the function has incorrect arguments.
        """
        if not callable(fn):
            raise ValueError("'%s' function must be callable!", str(fn))

        function_arguments = fn.__code__.co_varnames
        expected_arguments = ("method_name", "req", "resp", "kwargs")
        if function_arguments != expected_arguments:
            raise NameError(
                "function has incorrect arguments: '%s' != '%s'"
                % (function_arguments, expected_arguments)
            )

        self._suffix_method_caller = fn

    def add_route(self, uri_template, resource, *args, **kwargs):
        """Associate a templatized URI path with a resource.

        .. note:: this is the Falcon2 ported code with a small customization. Instead of using
            Falcon2 map_http_methods function, we start using our own customized function.

        Falcon routes incoming requests to resources based on a set of
        URI templates. If the path requested by the client matches the
        template for a given route, the request is then passed on to the
        associated resource for processing.

        If no route matches the request, control then passes to a
        default responder that simply raises an instance of
        :class:`~.HTTPNotFound`.

        .. seealso::`Routing <routing>`

        :param uri_template: A templatized URI. Care must be
            taken to ensure the template does not mask any sink
            patterns, if any are registered.
        :type uri_template: str

        .. seealso::`~.add_sink`

        :param resource: Object which represents a REST
            resource. Falcon will pass "GET" requests to on_get,
            "PUT" requests to on_put, etc. If any HTTP methods are not
            supported by your resource, simply don't define the
            corresponding request handlers, and Falcon will do the right
            thing.
        :type resource: instance

        .. note:: Any additional args and kwargs not defined above are passed
            through to the underlying router's ``add_route()`` method. The
            default router does not expect any additional arguments, but
            custom routers may take advantage of this feature to receive
            additional options when setting up routes.
        """

        # NOTE(richardolsson): Doing the validation here means it doesn't have
        # to be duplicated in every future router implementation.

        if FALCON_VERSION == 2:
            super().add_route(uri_template, resource, *args, **kwargs)
            return

        if not isinstance(uri_template, str):
            raise TypeError('uri_template is not a string')

        if not uri_template.startswith('/'):
            raise ValueError("uri_template must start with '/'")

        if '//' in uri_template:
            raise ValueError("uri_template may not contain '//'")

        method_map = map_http_methods(
            resource, kwargs.pop("suffix", None), self._suffix_method_caller
        )
        routing.set_default_responders(method_map)

        self._router.add_route(uri_template, method_map, resource, *args, **kwargs)

    @staticmethod
    def import_backend(name, options):
        """Import backend modules.

        :param name: module name.
        :type name: str
        :param options: options object that should be passed to the 'initialize' function.
        :type options: object

        :return: backend module.
        :rtype: module
        """
        backend = importlib.import_module('grapi.backend.%s' % name)
        if hasattr(backend, 'initialize'):
            backend.initialize(options)
        return backend
