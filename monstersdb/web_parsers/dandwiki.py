from html.parser import HTMLParser

import requests


class SRD35_HTMLParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(SRD35_HTMLParser, self).__init__(*arg, **kwargs)
        self.start = False
        # Informacion
        self.monster = []
        self.table = {}
        self.content = {}
        # Flags
        self.in_table = False
        self.in_key = False
        self.in_value = False
        self.in_content = False
        self.in_key_content = False
        self.in_value_content = False
        self.in_h3 = False
        # Temps
        self.temp_table = {}
        self.temp_content = {}
        self.temp_key = ''
        self.temp_value = ''
        self.temp_key_content = ''
        self.temp_value_content = ''

    def reset(self):
        super(SRD35_HTMLParser, self).reset()
        self.monster = []
        self.table = {}
        self.content = {}
        self.in_table = False
        self.in_key = False
        self.in_value = False
        self.in_key_content = False
        self.in_value_content = False
        self.in_h3 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'table' and 'monstats' in css:
            self.temp_table = {}
            self.in_table = True

        elif self.in_table and tag == 'th':
            self.temp_key = ''
            self.in_key = True

        elif self.in_table and tag == 'td':
            self.temp_value = ''
            self.in_value = True

        elif tag == 'h3':
            self.in_h3 = True
            self.in_content = True
            self.temp_content = {}


        elif self.in_h3 and tag == 'span' and css == 'mw-headline':
            self.temp_key_content = ''
            self.in_key_content = True

        elif self.in_h3 and tag == 'p':
            self.temp_value_content = ''
            self.in_value_content = True

        # elif self.in_table == False:
        #     if tag == 'p':
        #         self.temp_value_content = ''
        #         self.in_value_content = True

    def handle_endtag(self, tag):
        if self.in_table and tag == 'table':
            self.in_table = False

        elif self.in_key and tag == 'th':
            self.in_key = False

        elif self.in_value and tag == 'td':
            self.in_value = False

        elif tag == 'tr':
            if self.temp_key.endswith(':'):
                self.temp_key = self.temp_key[:-1]
            self.table[self.temp_key] = self.temp_value
            self.table.pop('','')

        elif self.in_key_content and tag == 'span':
            self.in_key_content = False

        elif self.in_value_content and tag == 'p':
            self.in_value_content = False

        elif self.in_content and tag == 'h3':
            self.in_h3 = False
            self.in_content = False
            self.content[self.temp_key_content] = self.temp_value_content

        # elif self.in_table == False: # Haciéndolo así solo me pilla el último párrafo y el "See Also"
        #     if tag == 'h3':
        #         self.in_value_content = False
        #         self.content['Descripción'] = self.temp_value_content


    def handle_data(self, data):
        data = data.replace('\n', '')

        if self.in_table and self.in_key:
            self.temp_key += data

        elif self.in_table and self.in_value:
            self.temp_value += data

        elif self.in_content and self.in_key_content:
            self.temp_key_content += data

        elif self.in_content and self.in_value_content:
            self.temp_value_content += data

        # elif self.in_table == False:
        #     if self.in_value_content:
        #         self.temp_value_content += data



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
    srd_parser = SRD35_HTMLParser()
    creature_url = 'https://www.dandwiki.com/wiki/SRD:Aboleth'
    print(creature_url)
    parse_url(srd_parser, creature_url)
    print(srd_parser.table)
    print(srd_parser.content)
    print(srd_parser.monster)



if __name__ == '__main__':
    main()
