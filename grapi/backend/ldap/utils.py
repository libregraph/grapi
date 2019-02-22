import codecs


_marker = object()


def _get_ldap_attr_value(attrs, name, default=_marker):
    values = attrs.get(name, _marker)
    if values is _marker or len(values) == 0:
        # Not found.
        if default is _marker:
            raise KeyError(name)
        return default

    return codecs.decode(values[0], 'utf-8')
