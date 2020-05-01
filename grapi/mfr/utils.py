# SPDX-License-Identifier: AGPL-3.0-or-later


def parse_accept_language(accept_lang):
    '''Parses HTTP Accept-Language header

       https://tools.ietf.org/html/rfc7231#section-5.3.5

       Lacks verification of languages per RFC: https://tools.ietf.org/html/rfc4647#section-2.1

       Returns a list of tuples with language and quality or an empty list
    '''

    languages = []
    accept_langs = accept_lang.split(',')

    for index, language in enumerate(accept_langs):
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
        # Multiple languages are given without a value, use precende as quality determinator
        elif index > 0:
            quality -= index / 100

        languages.append((lang, quality))

    languages.sort(key=lambda x: x[1])
    languages.reverse()

    return languages
