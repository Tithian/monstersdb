from html.parser import HTMLParser

import requests


class SRD35_HTMLParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(SRD35_HTMLParser, self).__init__(*arg, **kwargs)
        # Informacion
        self.tabla = {}
        self.contenido = {}
        # Flags
        self.in_table = False
        self.in_contenido = False

    def reset(self):
        super(SRD35_HTMLParser, self).reset()
        self.tabla = {}
        self.contenido = {}
        self.in_table = False
        self.in_contenido = False

    def handle_starttag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        pass


class ListCreaturesHTMLParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(ListCreaturesHTMLParser, self).__init__(*arg, **kwargs)
        self.start = False
        self.list_creatures = set()

    def handle_starttag(self, tag, attrs):
        if self.start:
            if tag == 'a':
                attrs = dict(attrs)
                if attrs.get('title', '').startswith('SRD:'):
                    self.list_creatures.add(attrs.get('href', ''))

        elif tag == 'span':
            attrs = dict(attrs)
            if attrs.get('id', None) == 'Creatures':
                self.start = True


def parse_url(parser, url):
    response = requests.get(url)
    if response.status_code == 200:
        parser.feed(response.text)


def main():
    list_creatures_parser = ListCreaturesHTMLParser()
    parse_url(list_creatures_parser, 'https://www.dandwiki.com/wiki/SRD:Creatures')

    srd_parser = SRD35_HTMLParser()
    for creature_path in sorted(list_creatures_parser.list_creatures):
        creature_url = 'https://www.dandwiki.com{path}'.format(path=creature_path)
        print(creature_url)
        parse_url(srd_parser, creature_url)
        srd_parser.tabla
        srd_parser.contenido
        # TODO guardar tabla y contenido en algun sitio
        srd_parser.reset()
        break


if __name__ == '__main__':
    main()
