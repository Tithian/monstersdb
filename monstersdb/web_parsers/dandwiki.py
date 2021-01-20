from html.parser import HTMLParser

import requests


class SRD35_HTMLParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(SRD35_HTMLParser, self).__init__(*arg, **kwargs)
        # import ipdb; ipdb.set_trace()  # debugging manual

        self.start = False
        # Informacion
        self.monster = []
        self.table = {}
        self.content = {}
        self.description = {}
        # Flags
        self.in_table = False
        self.in_key = False
        self.in_value = False
        self.in_combate = False
        self.in_p = False
        self.in_span = False
        self.start_description = False
        self.in_description = False
        self.finish = False
        # Temps
        self.temp_table = {}
        self.temp_key = ''
        self.temp_value = ''
        self.temp_combate = ''
        self.temp_description = ''

    def reset(self):
        super(SRD35_HTMLParser, self).reset()
        self.monster = []
        self.table = {}
        self.content = {}
        self.description = {}
        self.in_table = False
        self.in_key = False
        self.in_value = False
        self.in_combate = False
        self.in_p = False
        self.in_span = False
        self.start_description = False
        self.in_description = False
        self.finish = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'table' and 'monstats' in css:
            self.temp_table = {}
            self.in_table = True

        elif self.in_table:
            if tag == 'th':
                self.temp_key = ''
                self.in_key = True
            if tag == 'td':
                self.temp_value = ''
                self.in_value = True

        elif tag == 'h1' and 'firstHeading' in css:
            self.start_description = True

        elif tag == 'span' and 'headline' in css:
            css = attrs.get('id', '')
            self.start_description = True

            if tag == 'span' and 'COMBAT' in css:
                self.in_combate = True
                self.in_description = False
            elif tag == 'span' and 'Combat' in css:
                self.in_combate = True
                self.in_description = False
            elif tag == 'span' and 'Also' in css:
                self.in_description = False
                self.in_combate = False
                self.finish = True
            elif tag == 'span' and 'Characters' in css:
                self.in_description = False
                self.in_combate = False
                self.finish = True

        elif tag == 'a':
            title = attrs.get('title', '')
            if 'Main Page' in title:
                self.finish = True
                self.in_description = False
                self.in_combate = False
                self.start_description = False

        elif tag == 'caption':
            self.in_description = False
            self.finish = True
            self.in_combate = False

        elif self.start_description and tag == 'p':
            self.in_description = True



        elif self.in_combate and tag == 'p':
            self.in_p = True

    def handle_endtag(self, tag):
        if self.in_table:
            if tag == 'table':
                self.in_table = False
                self.monster.append(self.temp_table)
                self.monster.append(self.description)
                self.monster.append(self.content)
                self.temp_table = {}
                self.temp_description = ''
                self.temp_combate = ''

            elif self.in_key and tag == 'th':
                self.in_key = False

            elif self.in_value and tag == 'td':
                self.in_value = False

            elif tag == 'tr':
                if self.temp_key.endswith(':'):
                    self.temp_key = self.temp_key[:-1]
                self.temp_table[self.temp_key] = self.temp_value
                self.temp_key = ''
                self.temp_value = ''

        elif self.start_description and tag == 'p':
            self.temp_description.replace('Back to Main Page → 3.5e Open Game Content → '
                                          'System Reference Document → Creatures', '')
            if not self.description:
                if self.temp_description:
                    self.description['Descripción'] = self.temp_description

        elif self.in_combate and tag == 'p':
            self.in_p = False


        elif self.finish:
            self.temp_combate = self.temp_combate.replace('COMBAT', '')
            self.temp_combate = self.temp_combate.replace('Combat', '')
            if not self.content:
                self.content['Combate'] = self.temp_combate


    def handle_data(self, data):
        data = data.replace('\n', '')

        if self.in_table and self.in_key:
            self.temp_key += data

        elif self.in_table and self.in_value:
            self.temp_value += data

        elif not self.in_p and self.in_combate:
            self.temp_combate +=data

        elif self.in_description:
            self.temp_description += data



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
    parse_url(list_creatures_parser, 'https://www.dandwiki.com/wiki/Creatures')

    srd_parser = SRD35_HTMLParser()
    for creature_path in sorted(list_creatures_parser.list_creatures):
        creature_url = 'https://www.dandwiki.com{path}'.format(path=creature_path)
        print(creature_url)
        parse_url(srd_parser, creature_url)
        srd_parser.table.pop('', '')
        for monster in srd_parser.monster:
            print(monster)
        srd_parser.reset()


if __name__ == '__main__':
    main()
