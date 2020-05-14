# SPDX-License-Identifier: AGPL-3.0-or-later


def parse_accept_language(accept_language):
    '''Parses HTTP Accept-Language header

       https://tools.ietf.org/html/rfc7231#section-5.3.5

       Lacks verification of languages per RFC: https://tools.ietf.org/html/rfc4647#section-2.1

       Returns a list of tuples with language and quality or an empty list
    '''

    languages = []
    accept_languages = accept_language.split(',')

    index = 0
    for language in accept_languages:
        entry = language.strip().lower().replace('_', '-')

        if not entry:
            continue

        values = entry.split(';', 2)
        lang = values[0].strip()
        quality = 1

        # semicolon found, try to parse the possible quality field
        if len(values) == 2:
            # Ignore invalid values
            if not values[1].strip().startswith('q='):
                continue
            else:
                parts = values[1].split('=', 2)
                if len(parts) != 2:
                    continue
                try:
                    quality = float(parts[1])
                except ValueError:
                    continue
        # Multiple languages might be given without a value, use precedence as quality indicator
        else:
            quality -= index / 100
            index += 1

        languages.append((lang, quality))

        # Expand the languages with the "base" language if it consists out of two parts
        if '-' in lang:
            quality -= index / 100
            index += 1
            languages.append((lang.split('-')[0], round(quality, 2)))

    languages.sort(key=lambda x: x[1])
    languages.reverse()

    return languages
