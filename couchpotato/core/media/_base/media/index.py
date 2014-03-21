from string import ascii_letters
from hashlib import md5

from CodernityDB.tree_index import MultiTreeBasedIndex, TreeBasedIndex
from couchpotato.core.helpers.encoding import toUnicode, simplifyString


class MediaIndex(MultiTreeBasedIndex):
    _version = 3

    custom_header = """from CodernityDB.tree_index import MultiTreeBasedIndex"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(MediaIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'media' and (data.get('identifier') or data.get('identifiers')):

            identifiers = data.get('identifiers', {})
            if data.get('identifier') and 'imdb' not in identifiers:
                identifiers['imdb'] = data.get('identifier')

            ids = []
            for x in identifiers:
                ids.append(md5('%s-%s' % (x, identifiers[x])).hexdigest())

            return ids, None

    def run_identifiers(self, db, identifiers, with_doc = False):
        for x in identifiers:
            try:
                media = db.get('media', '%s-%s' % (x, identifiers[x]), with_doc = with_doc)
                return media
            except:
                pass


class MediaStatusIndex(TreeBasedIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(MediaStatusIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('status'):
            return md5(data.get('status')).hexdigest(), None


class MediaTypeIndex(TreeBasedIndex):
    _version = 1

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(MediaTypeIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return md5(key).hexdigest()

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('type'):
            return md5(data.get('type')).hexdigest(), None


class TitleSearchIndex(MultiTreeBasedIndex):
    _version = 1

    custom_header = """from CodernityDB.tree_index import MultiTreeBasedIndex
from itertools import izip
from couchpotato.core.helpers.encoding import simplifyString"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(TitleSearchIndex, self).__init__(*args, **kwargs)
        self.__l = kwargs.get('w_len', 2)

    def make_key_value(self, data):

        if data.get('_t') == 'media' and len(data.get('title', '')) > 0:

            out = set()
            title = str(simplifyString(data.get('title').lower()))
            l = self.__l
            title_split = title.split()

            for x in range(len(title_split)):
                combo = ' '.join(title_split[x:])[:32].strip()
                out.add(combo.rjust(32, '_'))
                combo_range = max(l, min(len(combo), 32))

                for cx in range(1, combo_range):
                    ccombo = combo[:-cx].strip()
                    if len(ccombo) > l:
                        out.add(ccombo.rjust(32, '_'))

            return out, None

    def make_key(self, key):
        return key.rjust(32, '_').lower()


class TitleIndex(TreeBasedIndex):
    _version = 1

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
from string import ascii_letters
from couchpotato.core.helpers.encoding import toUnicode, simplifyString"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '32s'
        super(TitleIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return self.simplify(key)

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('title') is not None:
            return self.simplify(data['title']), None

    def simplify(self, title):

        title = toUnicode(title)

        nr_prefix = '' if title[0] in ascii_letters else '#'
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return str(nr_prefix + title).ljust(32, '_')[:32]


class StartsWithIndex(TreeBasedIndex):
    _version = 1

    custom_header = """from CodernityDB.tree_index import TreeBasedIndex
from string import ascii_letters
from couchpotato.core.helpers.encoding import toUnicode, simplifyString"""

    def __init__(self, *args, **kwargs):
        kwargs['key_format'] = '1s'
        super(StartsWithIndex, self).__init__(*args, **kwargs)

    def make_key(self, key):
        return self.first(key)

    def make_key_value(self, data):
        if data.get('_t') == 'media' and data.get('title') is not None:
            return self.first(data['title']), None

    def first(self, title):
        title = toUnicode(title)
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return str(title[0] if title[0] in ascii_letters else '#').lower()