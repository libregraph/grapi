# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Backport Context from Falcon 2.0.0 to simplify context use and future
# compatibility with it.
#
# Copyright 2012-2017 by Rackspace Hosting, Inc. and other contributors,
# as noted in the individual source code files.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# NOTE(vytas): Although Context is effectively implementing the MutableMapping
#   interface, we choose not to subclass MutableMapping to stress the fact that
#   Context is, by design, a bare class, and the mapping interface may be
#   removed in a future Falcon release.
class Context:
    """
    Convenience class to hold contextual information in its attributes.
    This class is used as the default :class:`~.Request` and :class:`~Response`
    context type (see
    :attr:`Request.context_type <falcon.Request.context_type>` and
    :attr:`Response.context_type <falcon.Response.context_type>`,
    respectively).
    In Falcon versions prior to 2.0, the default context type was ``dict``. To
    ease the migration to attribute-based context object approach, this class
    also implements the mapping interface; that is, object attributes are
    linked to dictionary items, and vice versa. For instance:
    >>> context = falcon.Context()
    >>> context.cache_strategy = 'lru'
    >>> context.get('cache_strategy')
    'lru'
    >>> 'cache_strategy' in context
    True
    """

    def __contains__(self, key):
        return self.__dict__.__contains__(key)

    def __getitem__(self, key):
        # PERF(vytas): On CPython, using this mapping interface (instead of a
        #   standard dict) to get, set and delete items incurs overhead
        #   approximately comparable to that of two function calls
        #   (per get/set/delete operation, that is).
        return self.__dict__.__getitem__(key)

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)

    def __delitem__(self, key):
        self.__dict__.__delitem__(key)

    def __iter__(self):
        return self.__dict__.__iter__()

    def __len__(self):
        return self.__dict__.__len__()

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__.__eq__(other.__dict__)
        return self.__dict__.__eq__(other)

    def __ne__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__.__ne__(other.__dict__)
        return self.__dict__.__ne__(other)

    def __hash__(self):
        return hash(self.__dict__)

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, self.__dict__.__repr__())

    def __str__(self):
        return '{}({})'.format(type(self).__name__, self.__dict__.__str__())

    def clear(self):
        return self.__dict__.clear()

    def copy(self):
        ctx = type(self)()
        ctx.update(self.__dict__)
        return ctx

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def items(self):
        return self.__dict__.items()

    def keys(self):
        return self.__dict__.keys()

    def pop(self, key, default=None):
        return self.__dict__.pop(key, default)

    def popitem(self):
        return self.__dict__.popitem()

    def setdefault(self, key, default_value=None):
        return self.__dict__.setdefault(key, default_value)

    def update(self, items):
        self.__dict__.update(items)

    def values(self):
        return self.__dict__.values()
