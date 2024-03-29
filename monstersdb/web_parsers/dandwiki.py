import os
import shutil
import json
import glob
from html.parser import HTMLParser

import requests
import argparse
import logging


class BaseParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(BaseParser, self).__init__(*arg, **kwargs)
        self.start = False
        self.final_data = {}

    def reset(self):
        super(BaseParser, self).reset()
        self.start = False
        self.final_data = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'div' and 'mw-body-content' in css:
            self.start = True

    def handle_endtag(self, tag):
        if tag == 'hr':
            self.start = False


class NameParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(NameParser, self).__init__(*arg, **kwargs)
        self.temp_monster_name = ''
        self.in_monster_name = False

    def handle_starttag(self, tag, attrs):
        super(NameParser, self).handle_starttag(tag, attrs)
        if self.start:
            if tag == 'h1':
                if not self.temp_monster_name:
                    self.in_monster_name = True

    def handle_endtag(self, tag):
        if self.in_monster_name and tag == 'h1':
            self.final_data['Nombre'] = self.temp_monster_name.capitalize()
            self.in_monster_name = False
            self.start = False

    def handle_data(self, data):
        if self.in_monster_name:
            self.temp_monster_name += data


class MultiTableParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(MultiTableParser, self).__init__(*arg, **kwargs)
        # Informacion
        self.final_data = []
        self.total_value = ''
        self.total_key = ''
        # Flags
        self.in_table = False
        self.in_key = False
        self.in_value = False
        # Temps
        self.temp_table = {}
        self.temp_key = ''
        self.temp_value = ''

    def handle_starttag(self, tag, attrs):
        super(MultiTableParser, self).handle_starttag(tag, attrs)
        if self.start:
            attrs = dict(attrs)
            css = attrs.get('class', '')

            if tag == 'table':
                if 'monstats' in css:
                    cell = attrs.get('cellpadding')
                    self.temp_table = {}
                    self.in_table = True
                    if cell == '0':  # Es para quitar el conjuro que toma como una tabla en Worm_That_Walks
                        self.in_table = False

            elif self.in_table:
                if tag == 'th':
                    self.temp_key = ''
                    self.in_key = True
                if tag == 'td':
                    self.temp_value = ''
                    self.in_value = True

    def handle_endtag(self, tag):
        super(MultiTableParser, self).handle_endtag(tag)
        if self.in_table:
            if tag == 'table':
                self.in_table = False
                self.final_data.append(self.temp_table)
                self.temp_table = {}
            elif self.in_key and tag == 'th':
                self.in_key = False
                # Esto hace que si tiene varios valores la tabla, los concadene.
                if self.total_key:
                    self.total_key += '//' + self.temp_key
                else:
                    self.total_key += self.temp_key
            elif self.in_value and tag == 'td':
                self.in_value = False
                # Lo mismo que el comentario anterior.
                if self.total_value:
                    self.total_value += '//' + self.temp_value
                else:
                    self.total_value += self.temp_value

            elif tag == 'tr':
                if self.temp_key.endswith(':'):
                    self.temp_key = self.temp_key[:-1]
                    self.temp_table[self.temp_key] = self.total_value
                    self.temp_key = ''
                    self.total_value = ''
                    self.total_key = ''
                else:
                    self.temp_table['Monstruo y Nivel'] = self.total_key
                    self.total_key = ''

    def handle_data(self, data):
        if self.in_table:
            data = data.replace('\n', '')
            if self.in_key:
                self.temp_key += data
            elif self.in_value:
                self.temp_value += data


class DescriptionParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(DescriptionParser, self).__init__(*arg, **kwargs)
        self.start_description = False
        self.in_description = False
        self.in_toc = False
        self.h1_found = False
        self.h2_found = False
        self.temp_description = ''

    def handle_starttag(self, tag, attrs):
        super(DescriptionParser, self).handle_starttag(tag, attrs)

        if self.start:
            attrs = dict(attrs)
            css = attrs.get('class', '')
            if tag == 'div':
                # Esto es para quitar la tabla de contenido
                if 'toc' in css:
                    self.in_toc = True
            elif tag == 'h2':
                self.h2_found = True
            elif tag == 'h1':
                self.h1_found = True
            elif tag == 'span':
                self.in_description = False

            if not (self.in_toc and self.h2_found and self.h1_found):
                # SOLO ENTRA SI alguna es False
                if tag == 'table':
                    self.in_description = False
                elif tag == 'p':
                    self.in_description = True
                elif tag == 'h3':
                    h3_id = attrs.get('id', '')
                    if 'siteSub' not in h3_id:
                        self.start = False

    def handle_endtag(self, tag):
        super(DescriptionParser, self).handle_endtag(tag)
        if tag == 'div' and self.in_toc:
            self.in_toc = False
        elif tag == 'hr':
            clean_descr = self.temp_description.replace('\n\n', '')
            sin_wiki = clean_descr.partition('SEE WIKIPEDIA ENTRY:')
            sin_cap_wiki = sin_wiki[0].partition('See Wikipedia Entry:')
            if sin_cap_wiki[0]:
                if sin_cap_wiki[0].startswith('\n'):
                    self.final_data['Descripción'] = sin_cap_wiki[0].replace('\n', '', 1)
                    self.temp_description = ''
                else:
                    self.final_data['Descripción'] = sin_cap_wiki[0]
                    self.temp_description = ''
            self.start_description = False
            self.in_description = False

    def handle_data(self, data):
        if self.start and self.in_description:
            self.temp_description += data


class CombatParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(CombatParser, self).__init__(*arg, **kwargs)
        self.in_combat = False
        self.temp_combat = ''

    def handle_starttag(self, tag, attrs):
        super(CombatParser, self).handle_starttag(tag, attrs)
        if self.start:
            attrs = dict(attrs)
            css = attrs.get('class', '')
            if tag == 'span' and 'headline' in css:
                id_span = attrs.get('id', '').capitalize()
                if 'S' == id_span:
                    self.in_combat = False
                elif id_span.startswith('Combat'):
                    self.in_combat = True
                elif id_span.startswith('See'):
                    self.in_combat = False
                elif id_span.startswith('Creating'):  # Esto quita los apartados de creación de criaturas
                    self.in_combat = False
                elif 'characters' in id_span:
                    self.in_combat = False

            elif tag == 'hr':
                while '\n\n\n' in self.temp_combat:
                    self.temp_combat = self.temp_combat.replace('\n\n\n', '\n\n')
                if self.temp_combat:
                    clean_comb = self.temp_combat.replace('\n\n', '')
                    if clean_comb[:6].upper() == 'COMBAT':
                        clean_comb = clean_comb[6:]
                    if clean_comb.startswith('\n'):
                        clean_comb = clean_comb[1:]
                    # Esto lo quita en mayúsculas
                    sin_wiki = clean_comb.partition('SEE WIKIPEDIA ENTRY:')
                    # Esto lo quita en unos pocos que está en Capitalize
                    sin_cap_wiki = sin_wiki[0].partition('See Wikipedia Entry:')
                    # Esto lo quita en el true dragon
                    sin_entries = sin_cap_wiki[0].partition('Wikipedia Entries')
                    self.final_data['Combate'] = sin_entries[0]

    def handle_data(self, data):
        if self.in_combat:
            self.temp_combat += data


class ImportantEntriesParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(ImportantEntriesParser, self).__init__(*arg, **kwargs)
        self.final_data = []
        self.in_span = False
        self.important_entry = False
        self.in_important_key = False
        self.temp_entry = {}
        self.temp_entry_val = ''
        self.temp_entry_key = ''

    def handle_starttag(self, tag, attrs):
        super(ImportantEntriesParser, self).handle_starttag(tag, attrs)
        if self.start:
            attrs = dict(attrs)
            id_span = attrs.get('id', '')
            if tag == 'table':
                self.important_entry = False
            elif tag == 'span':
                while '\n\n\n' in self.temp_entry_val:
                    self.temp_entry_val = self.temp_entry_val.replace('\n\n\n', '\n\n')
                if self.temp_entry_val:
                    clean_comb = self.temp_entry_val.replace('\n\n', '')
                    if clean_comb.startswith('\n'):
                        clean_comb = clean_comb[1:]
                    # Esto lo quita en mayúsculas
                    sin_wiki = clean_comb.partition('SEE WIKIPEDIA ENTRY:')
                    # Esto lo quita en unos pocos que está en Capitalize
                    sin_cap_wiki = sin_wiki[0].partition('See Wikipedia Entry:')
                    # Esto lo quita en el true dragon
                    sin_entries = sin_cap_wiki[0].partition('Wikipedia Entries')
                    self.temp_entry[self.temp_entry_key.capitalize()] = sin_entries[0]
                    self.final_data.append(self.temp_entry)
                    self.temp_entry_val = ''
                    self.temp_entry_key = ''
                    self.temp_entry = {}
                self.in_span = True
                self.important_entry = False
                self.in_important_key = False
                things_to_take = ('CHARACTERS', 'TRAITS', 'DEVIL', 'BUILDING', 'DEMON', 'CONSTRUCTION', 'CREATING',
                                  'EQUIPMENT')
                if 'LIST' in id_span.upper():
                    self.important_entry = False
                else:
                    for elem in things_to_take:
                        if elem in id_span.upper():
                            self.important_entry = True
                            self.in_important_key = True

    def handle_endtag(self, tag):
        if self.start:
            if tag == 'span':
                self.in_span = False
                self.in_important_key = False

        elif tag == 'hr':
            self.important_entry = False

    def handle_data(self, data):
        if self.in_important_key:
            self.temp_entry_key += data
        elif self.important_entry:
            self.temp_entry_val += data


class RareTableParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(RareTableParser, self).__init__(*arg, **kwargs)
        # Informacion
        self.final_data = []
        self.table_name = ''
        self.total_values = []
        self.total_keys = []
        # Flags
        self.in_rare_table = False
        self.in_caption = False
        self.in_rare_key = False
        self.in_rare_value = False
        # Temps
        self.temp_key = ''
        self.temp_value = ''

    def handle_starttag(self, tag, attrs):
        super(RareTableParser, self).handle_starttag(tag, attrs)
        if self.start:
            attrs = dict(attrs)
            css = attrs.get('class', '')

            if tag == 'table':
                align = attrs.get('style', '')
                if 'text-align: right' in align:
                    self.in_rare_table = False
                elif 'monstats' in css:
                    cell = attrs.get('cellpadding')
                    self.in_rare_table = False
                    if cell == '0':  # Es para añadir el conjuro que toma como una tabla en Worm_That_Walks
                        self.in_rare_table = True
                else:
                    self.in_rare_table = True

            elif self.in_rare_table:
                if tag == 'caption':
                    self.table_name = ''
                    self.in_caption = True
                if tag == 'th':
                    self.temp_key = ''
                    self.in_rare_key = True
                if tag == 'td':
                    self.temp_value = ''
                    self.in_rare_value = True

    def handle_endtag(self, tag):
        super(RareTableParser, self).handle_endtag(tag)
        if self.in_rare_table:
            if tag == 'table':
                self.in_rare_table = False
                if self.table_name:
                    self.final_data.append(self.table_name)
                if self.total_keys:
                    self.final_data.append('CLAVES')
                    self.final_data.append(self.total_keys)
                if self.total_values:
                    self.final_data.append('VALORES')
                    self.final_data.append(self.total_values)
                self.table_name = ''
                self.total_keys = []
                self.total_values = []
            elif self.in_caption and tag == 'caption':
                self.in_caption = False
            elif self.in_rare_key and tag == 'th':
                self.in_rare_key = False
                if self.temp_key.endswith(':'):
                    self.temp_key = self.temp_key[:-1]
                self.total_keys.append(self.temp_key)
                self.temp_key = ''
            elif self.in_rare_value and tag == 'td':
                self.in_rare_value = False
                self.total_values.append(self.temp_value)
                self.temp_value = ''

    def handle_data(self, data):
        if self.in_rare_table:
            data = data.replace('\n', '')
            if self.in_caption:
                self.table_name += data
            elif self.in_rare_key:
                self.temp_key += data
            elif self.in_rare_value:
                self.temp_value += data


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


class Agrupation(object):
    def __init__(self):
        super(Agrupation, self).__init__()
        self.parsers = [NameParser,
                        MultiTableParser,
                        DescriptionParser,
                        CombatParser,
                        ImportantEntriesParser,
                        RareTableParser]
        self.data = []

    def parse_all(self, html_file):
        for cls in self.parsers:
            parser = cls()
            with open(html_file, 'r+', encoding='utf-8') as f:
                parser.feed(f.read())
                f.seek(0)
                if parser.final_data:
                    if isinstance(parser.final_data, list):
                        self.data.extend(parser.final_data)
                    else:
                        self.data.append(parser.final_data)


def parse_url(parser, url):
    response = requests.get(url)
    if response.status_code == 200:
        parser.feed(response.text)


def dumper_html(folder, to_print=False):
    """
    Esta función vuelca el contenido de los html a un directorio
    """
    # Si el directorio pasado como argumento no existe: Crea el directorio pasado como argumento
    if not os.path.isdir(folder):
        os.mkdir(folder)
    # Llama a la función que coge los enlaces de cada criatura
    parser = ListCreaturesHTMLParser()
    # Enlace donde están todos los enlaces de las criaturas
    url = 'https://www.dandwiki.com/wiki/Creatures'
    # Llama a la función que chequea con el parser indicado la url indicada (ambos arriba)
    parse_url(parser, url)
    # Por cada enlace que tenga el parser: Hace que el nombre sea igual a la dirección, pero solo a partir de los ':'
    for path in parser.list_creatures:
        name = path[path.rfind(':') + 1:]
        # Le da formato al interior del placeholder {} con unacadena fuyo formato es igual a la variable nombre
        # reemplazando los espacios por guiones bajos
        filename = '{}.html'.format(name.replace(' ', '_'))

        response = requests.get('https://www.dandwiki.com{}'.format(path))
        filename = os.path.join(folder, filename)
        with open(filename, 'wb') as f:
            f.write(response.content)
            if to_print:
                print(filename)


def to_json(html_folder, json_folder, to_print=False):
    for path in glob.glob(os.path.join(html_folder, '*.html')):
        parsers = Agrupation()
        parsers.parse_all(path)
        filename = os.path.basename(path)
        filename = os.path.join(json_folder, filename)
        filename = filename.replace('.html', '.json')
        with open(filename, 'w') as f2:
            response = json.dumps(parsers.data, indent=2)
            f2.write(response)
            if to_print:
                print(filename)


def save_file(json_file, data):
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)


class SRD35_JsonClean(object):
    def __init__(self, json_file: str):
        self.json_file: str = json_file
        with open(self.json_file) as f:
            self.initial_data = json.load(f)

        self.final_data = []
        self.tables = []
        self.tabla = {}
        self.num_clave = 0
        self.num_valor = 0

        self.filename = os.path.basename(self.json_file)
        self.indexes = len(self.initial_data)
        self.enumerated_data = enumerate(self.initial_data)

    def excluyendo_ficheros(self, to_print=False) -> bool:
        files_to_exclude = ('Beholder',
                            'Creatures_by_Type',
                            'Creatures_by_CR',
                            'System_Reference_Document',
                            'Creature_Types')
        found = False

        if self.initial_data:
            found = True
            if self.filename.replace('.json', '') in files_to_exclude:
                found = False

        elif not self.initial_data:
            found = False

        if not found:
            if 'Demon' in self.json_file:
                pass
            elif 'Devil' in self.json_file:
                pass
            else:
                file = (os.path.realpath(self.json_file))
                dir_path = (os.path.dirname(filename))
                excluded_folder = os.path.join(dir_path, 'EXCLUDED')
                if not os.path.isdir(excluded_folder):  # Si el directorio pasado como argumento no existe:
                    os.mkdir(excluded_folder)  # Crea el directorio pasado como argumento
                shutil.move(file, excluded_folder)
                if to_print:
                    print(filename)

    def insertando_titulos(self, to_print=False) -> None:
        name_found = False
        for key, val in self.initial_data[0].items():
            if 'Nombre' in key:
                name_found = True
        if not name_found:
            with open(self.json_file, 'w') as f2:
                new_index = {}
                old_name = os.path.basename(self.json_file.replace('.json', ''))
                new_name = '{}'.format(old_name.replace('_', ' '))
                new_index['Nombre'] = new_name
                self.initial_data.insert(0, new_index)
                self.final_data = json.dumps(self.initial_data, indent=2)
                f2.write(self.final_data)
                if to_print:
                    print(self.json_file)

    def organizando_tipos(self, to_print=False) -> None:
        files_to_exclude = []
        criatura_tipo = False

        to_tipo = ['Air_Elemental.json',
                   'Animated_Object.json',
                   'Arrowhawk.json',
                   'Astral_Construct.json',
                   'Earth_Elemental.json',
                   'Fire_Elemental.json',
                   'Hoary_Hunter.json',
                   'Water_Elemental.json',
                   'Devil.json',
                   'Demon.json',
                   'Elemental.json'
                   'Dire_Animal.json']

        filename = (os.path.realpath(self.json_file))
        monster = os.path.basename(filename)
        dir_name = (os.path.dirname(filename))
        tipos_folder = os.path.join(dir_name, 'TIPOS')
        dragon_folder = os.path.join(tipos_folder, 'DRAGONES')
        if not os.path.isdir(dragon_folder):
            os.makedirs(dragon_folder)
        with open(self.json_file, 'r+') as f:
            data = json.load(f)
            if isinstance(data[1], dict):
                if 'Monstruo y Nivel' in data[1]:
                    criatura_tipo = True
                if 'Size/Type' in data[1]:
                    criatura_tipo = True
            for elem in to_tipo:
                if monster == elem:
                    criatura_tipo = False
            if not criatura_tipo:
                shutil.copy2(filename, tipos_folder)
                files_to_exclude.append(filename)
                if to_print:
                    if not 'Dragon' in monster:
                        print('El archivo ', monster, ' ha sido movido a la carpeta TIPOS')
                f.close()
                os.remove(filename)
        for path in glob.glob('{}/*.json'.format(tipos_folder)):
            is_dragon = False
            with open(path, 'r+') as f:
                data = json.load(f)
                enumerated_data = enumerate(data)
                if 'Celestial_Creature' in path:
                    pass
                elif 'Ghost' in path:
                    pass
                elif 'Half-Dragon' in path:
                    pass
                elif 'Fiendish_Creature' in path:
                    pass
                else:
                    for index, elem in enumerated_data:
                        try:  # TODO arreglar esto
                            for key, val in elem.items():
                                if 'dragon' in val.lower():
                                    is_dragon = True
                        except:
                            pass
                    if is_dragon:
                        filename = (os.path.realpath(path))
                        shutil.copy2(filename, dragon_folder)
                        if to_print:
                            print('El archivo ', monster, ' ha sido movido a la carpeta DRAGONES')
                        f.close()
                        os.remove(filename)

    def insertando_claves(self, to_print=False) -> None:
        mon_y_niv_found = False
        filename = os.path.basename(self.json_file)
        if 'Monstruo y Nivel' in self.initial_data[1]:
            mon_y_niv_found = True
            for key, val in self.initial_data[1].items():
                if not val:
                    if to_print:
                        print(filename, ' No tiene valor en ', key, '. Se ha añadido un "\u2014"')
                    dic = self.initial_data[1]
                    dic[key] = '\u2014'
                    self.final_data = json.dumps(self.initial_data, indent=2)
                    with open(self.json_file, 'w') as f:
                        f.write(self.final_data)
                        if to_print:
                            print(filename)
        if not mon_y_niv_found:
            if 'Nombre' in self.initial_data[0].keys():
                mon_y_niv_val = self.initial_data[0].get('Nombre')
                dic = self.initial_data[1]
                dic['Monstruo y Nivel'] = mon_y_niv_val
                self.final_data = json.dumps(self.initial_data, indent=2)
                with open(self.json_file, 'w') as f:
                    f.write(self.final_data)
                    if to_print:
                        print(filename)

    def insertando_descripciones(self, to_print=False) -> None:
        descr_found = False
        filename = os.path.basename(self.json_file)
        key_finder = 'Descripción'

        for elem in self.initial_data:
            if isinstance(elem, dict):
                if elem.get(key_finder) is not None:
                    descr_found = True

        if not descr_found:
            if 'Astral_Construct' in filename:
                self.initial_data.append({'Descripci\u00f3n': 'Astral constructs are brought into being by the '
                                                              'metacreativity power astral construct. They are formed'
                                                              ' from raw ectoplasm (a portion of the astral medium '
                                                              'drawn into the Material Plane). The power points spent'
                                                              ' by the construct\u2019s creator during the '
                                                              'manifestation of the power determine the level of the'
                                                              ' astral construct created. However, even astral '
                                                              'constructs of the same level vary somewhat from each'
                                                              ' other, depending on the whims of their creators.'})
                self.final_data = self.initial_data
            if 'Advanced_Mummy' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = [{'Descripci\u00f3n': 'Mummies are preserved corpses animated '
                                                                             'through the auspices of dark desert gods '
                                                                             'best forgotten.\nMost mummies are 5 to 6'
                                                                             ' feet tall and weigh about 120 pounds.'
                                                                             '\nMummies can speak Common, but seldom '
                                                                             'bother to do so.'}]
            if 'Behemoth_Eagle' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Behemoths are outsiders in animal form that are of epic proportions, '
                                          'even larger and more powerful than dire animals.\nBehemoths resemble '
                                          'natural animals in almost all respects, but they are grossly larger than '
                                          'their natural counterparts, hailing from beyond the Prime Material plane. '
                                          'They are more intelligent than their mundane counterparts, and their '
                                          'otherworldliness confers a level of magical fortitude not found in '
                                          'earthbound versions.\nA behemoth eagle is an intelligent, keen-eyed bird of '
                                          'prey that sometimes associates with good creatures. It stands about 20 feet '
                                          'tall, with a wingspan of up to 80 feet.'}]
            if 'Behemoth_Gorilla' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Behemoths are outsiders in animal form that are of epic proportions, '
                                          'even larger and more powerful than dire animals.\nBehemoths resemble '
                                          'natural animals in almost all respects, but they are grossly larger than '
                                          'their natural counterparts, hailing from beyond the Prime Material plane. '
                                          'They are more intelligent than their mundane counterparts, and their '
                                          'otherworldliness confers a level of magical fortitude not found in '
                                          'earthbound versions.\nA behemoth gorilla stands 25 feet tall or more and '
                                          'weighs close to 20,000 pounds. It has long claws and sharp teeth.'}]
            if 'Brachyurus' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Brachyuruses are the primordial stock from which all lesser wolves and '
                                          'canines devolved. The mythological Fenris Wolf itself springs directly '
                                          'from brachyurus stock.\nBrachyuruses appear as extraordinarily large wolves '
                                          'with bristling mane of white and burnt red fur. Their teeth and claws, '
                                          'even for their extreme size, seem overlarge, but not in the least clumsy. '
                                          'The howl of a brachyurus can frighten even the most hardened, experienced '
                                          'adventurer.\nBrachyuruses roam ancient savannahs lost to time, otherplanar '
                                          'wilds, or as single individuals among their lesser kin in worlds where '
                                          'their presence is generally unrealized. Esoteric hunters prize brachyurus '
                                          'pelts, though more often than not such a hunter becomes the hunted.'
                                          '\nBrachyuruses can speak Common and can communicate with all wolves.'}]
            if 'Centipede_Swarm' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'A centipede swarm is a crawling mass of voracious centipedes that can climb '
                                          'over obstacles to get at prey.\n'}]
            if 'Cerebrilith' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Cerebriliths are demons whose already fearsome powers are augmented by '
                                          'psionics. They are specialists that join demonic armies only in response to'
                                          ' specific requirements (such as the need to defeat mortal psionic creatures '
                                          'and characters). When not so occupied, they continually develop and train'
                                          ' their already impressive mental abilities (alone or in small groups),'
                                          ' usually by stalking mortals.\nCerebriliths stop at nothing to slay'
                                          ' intelligent foes. They delight in extracting the brains of their victims'
                                          ', examining them in hopes of prying loose new insights into the mental'
                                          ' arts.'}]
            if 'Flesh_Harrower_Puppeteer' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Regular puppeteers (see above) are psionic parasites that directly control '
                                          'the minds of their hosts. But sometimes, a more direct method of subjugation'
                                          ' requires violence, in the form of flesh harrowers (also called dire '
                                          'puppeteers).\nThough it is little understood, the life cycle of a regular '
                                          'puppeteer involves laying tiny eggs. At its option, a puppeteer can mentally'
                                          ' manipulate any egg to produce a dire puppeteer instead of the standard, '
                                          'smaller version. Though unendowed with the ability to control the minds of '
                                          'others, a dire puppeteer can often simply slay a threat directly.'}]
            if 'Folugub' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Folugubs dissolve and eat crystals; the tongue turns crystalline '
                                          'objects(including gems) into a slimy goo, which the folugub then slurps up. '
                                          'Folugubs are the bane of psionically equipped parties, since so many psionic'
                                          ' items contain or are composed completely of crystal.'}]
            if 'Frost_Giant_Jar' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Frost giants are justifiably feared as brutal and wantonly destructive '
                                          'raiders.\nA frost giant’s hair can be light blue or dirty yellow, and its '
                                          'eyes usually match its hair color. Frost giants dress in skins and pelts, '
                                          'along with any jewelry they own. Frost giant warriors add chain shirts and '
                                          'metal helmets decorated with horns or feathers.\nAn adult male is about 15 '
                                          'feet tall and weighs about 2,800 pounds. Females are slightly shorter and '
                                          'lighter, but otherwise identical with males. Frost giants can live to be '
                                          '250 years old.\nA frost giant’s bag usually contains 1d4+1 throwing rocks, '
                                          '3d4 mundane items, and the giant’s personal wealth. Everything in a frost '
                                          'giant’s bag is old, worn, dirty, and smelly, making the identification of '
                                          'any valuable items difficult.'}]
            if 'Gray_Glutton' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'The gray glutton is a terrifying predator that lives only to eradicate '
                                          'psionic creatures and characters. The single-minded fury with which it '
                                          'tracks down and eradicates psionic individuals is stunning. Fortunately '
                                          'for psionic creatures everywhere, gray gluttons are rare, being an '
                                          'artificial species.\nGray gluttons are descended from the victims of '
                                          'twisted experimentation on individuals who had already been victimized '
                                          'by psionics-using enemies. Filled with hatred for those who wield psionics,'
                                          ' these poor souls were perfect fodder for arcane spellcasters seeking a '
                                          'weapon against their psionic foes. The mages who initiated the magical '
                                          'breeding program twisted once-human bodies into shapes so extreme that '
                                          'sentience itself was extinguished. All that remains is an instinctual hate'
                                          ' for all things psionic. The monsters are named not for the color of their'
                                          ' hide, but for the psionic-infused gray matter they crave above all.'}]
            if 'Grimlock' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Grimlocks are natives of the deep places beneath the earth but come to the '
                                          'surface to raid for slaves and pillage. While there, they lurk in '
                                          'mountainous terrain, which hides them well. They prefer raw, fresh meat - '
                                          'preferably human.\nExtremely xenophobic, grimlocks are normally encountered'
                                          ' in small patrols or packs on the surface. Underground, they may form larger'
                                          ' communities that are led by powerful grimlocks or by some more intelligent'
                                          ' creature, such as a medusa or a mind flayer.\nGrimlocks speak their own'
                                          ' language and Common.'}]
            if 'Hieracosphinx' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Of all the sphinxes, only these creatures are evil at heart. They are '
                                          'always male. They spend much of their time searching for a gynosphinx but '
                                          'are generally just as happy to maul someone.'}]
            if 'Human' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Humans (Homo sapiens) are a species of highly intelligent primates. Humans '
                                          'are terrestrial animals, characterized by their erect posture and bipedal '
                                          'locomotion; high manual dexterity and heavy tool use compared to other '
                                          'animals; open-ended and complex language use compared to other animal '
                                          'communications; larger, more complex brains than other primates; '
                                          'and highly advanced and organized societies.'}]
            if 'Iron_Colossus' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'An iron colossus is at least 80 feet tall and weighs around 350,000 pounds.'
                                          ' It can be fashioned in any manner, just like a stone colossus, although '
                                          'it almost always displays armor of some sort. Its features are much smoother'
                                          ' than those of a stone colossus. Iron colossi sometimes wield Huge exotic '
                                          'weapons in one hand.\nAn iron colossus cannot speak or make any vocal '
                                          'noise.'}]
            if 'Legendary_Bear' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'A legendary bear doesn’t usually attack humans despite its great strength.'
                                          ' Most of the bear’s diet consists of | plants and fish'}]
            if 'Legendary_Tiger' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'The legendary tiger is among the fiercest and most dangerous land predators'
                                          ' in the animal kingdom, measuring 8 to 10 feet long and weighing up to '
                                          '600 pounds.'}]
            if 'Leonal' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'One of the most powerful guardinal forms, a leonal is every bit as regal as'
                                          ' a lion of the Material Plane. As a foe, it can be just as terrifying, '
                                          'bellowing mighty roars and slashing with razor-sharp claws.'}]
            if 'Prismasaurus' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'The prismasaurus’s dazzling scales create a deadly rainbow of effects for '
                                          'all who behold it.\nA prismasaurus is about 20 feet long from nose to base '
                                          'of tail, and stands around 8 feet tall at the shoulder. It has a bony ridge'
                                          ' that runs from the back of its neck all the way down to the base of its'
                                          ' tail that is covered with special crystalline scales. The creature’s snout'
                                          ' is elongated, and it possesses a jaw full of powerful, crushing teeth. The'
                                          ' tip of a prismasaurus’s tail is a thick, bony bulge with horny protrusions'
                                          ' all over it.'}]
            if 'Rat_Swarm' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'A rat swarm is a mass of teeming, famished, disease-ridden rats. A swarm '
                                          'is composed of individuals very much like the rat described on the Animals'
                                          ' section, but in such great numbers, rats can become implacable hunters'
                                          ' capable of killing a human with hundreds of bites.\nA rat swarm sometimes'
                                          ' can be found in the sewers and foundations of human cities.'}]
            if 'Ruin_Swarm' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'A ruin swarm is composed of tens of thousands of vermin acting as a single '
                                          'malevolent organism—a flying ooze of colossal size.\nA ruin swarm appears as'
                                          ' an amorphous, mutable cloud of darkness 100 feet or more in diameter that'
                                          ' rises into the sky like billows of smoke marking a scene of destruction.'
                                          ' A swarm emits a thunderous roar that can be heard (as a rumbling drone) '
                                          'from up to a mile away; within a distance of 90 feet from a swarm, its roar'
                                          ' drowns out all other sound. As the flying ooze wings through the air, its'
                                          ' shape constantly spirals, twists, and mutates, and sometimes even divides'
                                          ' into two or more distinct units before rejoining again moments later.\nA '
                                          'ruin swarm originates in areas of magical contamination or leakage, or '
                                          'possibly through the design of an arcane experimentalist. Once formed, a'
                                          ' ruin swarm is for all intents and purposes a single organism of the ooze'
                                          ' type-—its individual particulates have no more bearing on its '
                                          'vulnerabilities or powers.\nA ruin swarm possesses vestigial intelligence '
                                          'but speaks no languages.'}]
            if 'Spider_Swarm' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'A spider swarm is a scuttling horde of venomous spiders.'}]
            if 'Udoroot' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'Udoroots are innocuous-looking carnivorous plants that use psionic powers '
                                          'to overcome other creatures, which it then uses as fertilizer.\nBy far the'
                                          ' largest part of an udoroot is its massive, bulbous root system, the '
                                          'bottommost tip of which can reach 30 feet below the surface. An udoroot '
                                          'sends six shoots to the surface, each of which culminates in a “crown” '
                                          'resembling a mature sunflower with reddish seeds and white petals. The '
                                          'seeds are tough but nutritious and can be made into bread if ground.\nA '
                                          'subterranean version of the udoroot grows “upside down” near the edges of'
                                          ' Underdark communities.'}]
            if 'Umbral_Blot' in filename:
                insert_at = 2  # Index at which you want to insert item

                self.final_data = self.initial_data[:]  # Created copy of list "a" as "b".
                # Skip this step if you are ok with modifying the original list

                self.final_data[insert_at:insert_at] = \
                    [{'Descripci\u00f3n': 'A hovering sphere of absolute void, an umbral blot (sometimes called a '
                                          'blackball) is an extraordinarily dangerous opponent to any who come into '
                                          'contact with it.\nWhen at rest, a blackball appears exactly like an '
                                          'overlarge sphere of annihilation, a sphere of utter darkness. In fact, '
                                          'sometimes one will be encountered by an arcane caster armed with a talisman'
                                          ' of the sphere, who commands it in the mistaken belief it is merely a '
                                          'sphere of annihilation and not the far more dangerous creature it actually'
                                          ' is. The umbral blot sometime chooses to obey its pseudo-master for a time,'
                                          ' before turning on her at the most inopportune time and disintegrating her'
                                          ' for her presumption.\nSome sages declare that the Old Ones, the gods who'
                                          ' were before the gods of today, created umbral blots as messengers and '
                                          'sometimes assassins. A few even maintain that they were called “Assassins'
                                          ' of the Elder Gods” in certain ancient texts because, having been created'
                                          ' by the forgotten gods of yore, they destroyed their creators and have '
                                          'since roamed the cosmos idly, searching for any who may have escaped them.'
                                          '\nAn umbral blot is perfectly silent; it never speaks. Perhaps it '
                                          'understands the lost language of the Old Ones, but if so, no others '
                                          'are left to converse with now.'}]
            with open(self.json_file, 'w') as f:
                self.final_data = json.dumps(self.final_data, indent=2)
                f.write(self.final_data)
                if to_print:
                    print('Se ha añadido una Descripción a ', filename)

    def eliminando_entradas(self, to_print=False):
        filename = os.path.basename(self.json_file)
        index = len(self.initial_data)
        if index == 5:
            inside = self.initial_data[4]
            if isinstance(inside, dict):
                for key, val in inside.items():
                    if not val:
                        del self.initial_data[4]
                        with open(self.json_file, 'w') as f:
                            self.final_data = json.dumps(self.initial_data, indent=2)
                            f.write(self.final_data)
                            if to_print:
                                print(
                                    'El archivo', filename, 'tenía la siguiente entrada innecesaria:'
                                    , inside, '. Ha sido eliminada')

    def eliminando_back_to_main(self, to_print=False):
        filename = os.path.basename(self.json_file)
        index = len(self.initial_data)
        fix = False
        if index == 5:
            inside = self.initial_data[4]
            for key, val in inside.items():
                if 'Back to' in val:
                    fix = True
                    pos = val.find('Back to Main Page')
                    change = val[:pos]
                    inside[key] = change
        if fix:
            with open(self.json_file, 'w') as f:
                self.final_data = json.dumps(self.initial_data, indent=2)
                f.write(self.final_data)
                if to_print:
                    print(
                        'Se ha eliminado "Back to Main Page" de', filename)

    def arreglando_tablas(self, to_print=False) -> None:
        en_claves = False
        en_valores = False
        t_name = {}
        claves = ''
        keys = 0
        self.tables = []

        for index, elem in self.enumerated_data:
            if isinstance(elem, str):
                if elem == 'CLAVES':
                    en_claves = True
                elif elem == 'VALORES':
                    en_valores = True
                else:
                    t_list = []
                    t_list.append(elem)
                    if 'Air' in self.filename:
                        t_name['Table Name'] = ['Air Elemental Sizes']
                    elif 'Worm_That_Walks' in self.filename:
                        t_name['Table Name'] = ['Gathering Of Maggots']
                    else:
                        t_name['Table Name'] = t_list[0:]
            elif isinstance(elem, list):
                if en_claves:
                    claves = elem
                    en_claves = False
                    keys = len(claves)
                elif en_valores:
                    valores = elem
                    en_valores = False
                    if 'Air' in self.filename:
                        hab_esp = []
                        for index, elem in enumerate(claves):
                            if '—––—— ' in elem:
                                hab_esp = str(elem.replace('—––—— ', '')).replace(' ——––—', '')
                            elif index < 3:
                                pass
                            elif index > 6:
                                self.tabla[hab_esp + ' ' + elem] = valores[index - 4::keys]
                            else:
                                self.tabla[elem] = valores[index - 4::keys]
                    elif 'Fire' in self.filename:
                        t_name['Table Name'] = claves[0:1]
                        for index, elem in enumerate(claves[1:]):
                            self.tabla[elem] = valores[index::keys]
                    elif 'Water' in self.filename:
                        hab_esp = []
                        for index, elem in enumerate(claves):
                            if '––—––—— ' in elem:
                                hab_esp = str(elem.replace('––—––—— ', '')).replace(' ——––––—', '')
                            elif index < 3:
                                pass
                            elif index > 6:
                                self.tabla[hab_esp + ' ' + elem] = valores[index - 4::keys]
                            else:
                                self.tabla[elem] = valores[index - 4::keys]
                    elif 'Worm_That_Walks' in self.filename:
                        for index, elem in enumerate(claves):
                            self.tabla['Escuela'] = valores[0]
                            self.tabla[elem] = valores[index + 1::keys]
                    else:
                        for index, elem in enumerate(claves):
                            self.tabla[elem] = valores[index::keys]
            else:
                self.final_data.append(elem)
            if t_name:
                self.tables.append(t_name)
                t_name = {}

            if self.tabla:  # Aquí si pongo un elif en los Fire Elemental no me coge la tabla
                self.tables.append(self.tabla)
                self.tabla = {}

        if self.tables:
            print(self.filename)
            for elem in self.tables:
                print(elem)
                self.final_data.append(elem)
            print('\n')
            save_file(self.json_file, self.final_data)
            if to_print:
                print('Se han arreglado las tablas de:', self.filename)

    def arreglando_tablas_tipo(self, to_print=False) -> None:
        zomb_esk = ['Zombie.json', 'Skeleton.json', 'Vampire.json', 'Fiendish_Creature.json']
        en_claves = False
        en_valores = False
        t_name = {}
        claves = ''
        keys = 0
        self.tables = []

        for index, elem in self.enumerated_data:
            if isinstance(elem, str):
                if elem == 'CLAVES':
                    en_claves = True
                    self.num_clave += 1
                elif elem == 'VALORES':
                    en_valores = True
                    self.num_valor += 1
                else:
                    t_list = []
                    t_list.append(elem)
                    if 'Air' in self.filename:
                        if self.num_clave == 0:  # Añade solo el nombre para la tabla de todos los tamaños
                            t_name['Table Name'] = ['Air Elemental Sizes']
                    elif 'Earth' in self.filename:
                        if self.num_clave == 0:
                            t_name['Table Name'] = t_list[0:]
                    elif 'Water' in self.filename:
                        if self.num_clave == 0:
                            t_name['Table Name'] = t_list[0:]
                    else:
                        t_name['Table Name'] = t_list[0:]
            elif isinstance(elem, list):
                if en_claves:
                    claves = elem
                    en_claves = False
                    keys = len(claves)
                elif en_valores:

                    valores = elem
                    en_valores = False
                    if 'Air' in self.filename:
                        hab_esp = []
                        # Coge la tabla de todos los tamaños y excluye las individuales
                        if self.num_clave == 1:
                            for index, elem in enumerate(claves):
                                if '—––—— ' in elem:
                                    hab_esp = str(elem.replace('—––—— ', '')).replace(' ——––—', '')
                                elif index < 3:
                                    pass
                                elif index > 6:
                                    self.tabla[hab_esp + ' ' + elem] = valores[index - 4::keys - 4]
                                else:
                                    self.tabla[elem] = valores[index - 4::keys - 4]
                    elif 'Earth' in self.filename:
                        if self.num_clave == 1:
                            for index, elem in enumerate(claves):
                                self.tabla[elem] = valores[index::keys]
                    elif 'Fire' in self.filename:
                        if self.num_clave == 1:
                            t_name['Table Name'] = claves[0:1]
                            for index, elem in enumerate(claves[1:]):
                                self.tabla[elem] = valores[index::keys]
                    elif 'Water' in self.filename:
                        hab_esp = []
                        if self.num_clave == 1:  # ver comentario en if 'Air'
                            for index, elem in enumerate(claves):
                                if '––—––—— ' in elem:
                                    hab_esp = str(elem.replace('––—––—— ', '')).replace(' ——––––—', '')
                                elif index < 3:
                                    pass
                                elif index > 6:
                                    self.tabla[hab_esp + ' ' + elem] = valores[index - 4::keys - 4]
                                else:
                                    self.tabla[elem] = valores[index - 4::keys - 4]
                    elif 'Monstrous' in self.filename:
                        if self.num_clave == 1:
                            for index, elem in enumerate(claves):
                                self.tabla[elem] = valores[index - 3:-3:keys - 3]
                        else:
                            for index, elem in enumerate(claves):
                                self.tabla[elem] = valores[index::keys]
                    elif self.num_clave == 0:  # Esto es para las tablas que no tienen CLAVES definidas
                        if 'Phrenic_Creature.json' == self.filename:
                            self.tabla[valores[0]] = valores[2::2]
                            self.tabla[valores[1]] = valores[3::2]
                        elif 'Skeleton.json' == self.filename:
                            if self.num_valor == 1:
                                t_name['Table Name'] = ['Armor Class Bonus']
                            elif self.num_valor == 2:
                                t_name['Table Name'] = ['Damage by Size']
                            keys = valores[::2]
                            values = valores[1::2]
                            self.tabla = {keys[i]: values[i] for i in range(len(keys))}
                        elif 'Zombie.json' == self.filename:
                            if self.num_valor == 1:
                                t_name['Table Name'] = ['Armor Class Bonus']
                            elif self.num_valor == 2:
                                t_name['Table Name'] = ['Damage by Size']
                            keys = valores[::2]
                            values = valores[1::2]
                            self.tabla = {keys[i]: values[i] for i in range(len(keys))}
                    else:
                        for index, elem in enumerate(claves):
                            self.tabla[elem] = valores[index::keys]
            else:
                self.final_data.append(elem)
            if t_name:
                self.tables.append(t_name)
                t_name = {}

            if self.tabla:  # Aquí si pongo un elif en los Fire Elemental no me coge la tabla
                self.tables.append(self.tabla)
                self.tabla = {}

        if self.tables:
            for elem in self.tables:
                self.final_data.append(elem)
            save_file(self.json_file, self.final_data)
            if to_print:
                print('Se han arreglado las tablas de:', self.filename)

    def arreglando_tablas_dragones(self, to_print=False) -> None:
        filename = os.path.basename(self.json_file)
        indexes = len(self.initial_data)
        enumerated_data = enumerate(self.initial_data)
        tables = []
        notes = []
        num_clave = 0

        if 'True' in filename:
            for index, elem in enumerated_data:
                tname = {}
                tabla = {}
                if isinstance(elem, str):
                    if elem == 'CLAVES':
                        en_claves = True
                    elif elem == 'VALORES':
                        en_valor = True
                    else:
                        tabla['Table Name'] = str(elem)
                if isinstance(elem, list):
                    if en_claves:
                        claves = elem
                        num_clave += 1
                        en_claves = False
                    elif en_valor:
                        valores = elem
                        en_valor = False
                        if isinstance(self.initial_data[3], str):
                            if num_clave == 1:
                                notes.append(valores[21:23])
                                del valores[21:23]
                                for index, elem in enumerate(claves):
                                    tabla[elem] = valores[index::len(claves)]
                            elif num_clave == 3:
                                notes.append(valores[56])
                                del valores[56]
                                for index, elem in enumerate(claves):
                                    tabla[elem] = valores[index::len(claves)]
                            elif num_clave == 4:
                                while '' in claves:
                                    claves.remove('')
                                while '' in valores:
                                    valores.remove('')
                                tabla[str(claves[0]).replace('————— ', '').replace(' —————', '')] = claves[1:5]
                                tabla[valores[0] + ' ' + valores[1]] = valores[2:6]
                                tabla[valores[0] + ' ' + valores[6]] = valores[7:11]
                                tabla[valores[11] + ' ' + valores[12]] = valores[13:17]
                            elif num_clave == 5:
                                tname['Table Name'] = 'Epic Dragon Age Categories'
                                tables.append(tname)
                                for index, elem in enumerate(claves):
                                    if elem == '':
                                        pass
                                    else:
                                        tabla[elem] = valores[index::len(claves)]
                            elif num_clave == 6:
                                tname['Table Name'] = 'Epic Dragon Space and Reach'
                                tables.append(tname)
                                for index, elem in enumerate(claves):
                                    tabla[str(elem).replace(' ', '')] = valores[index::len(claves)]
                            elif num_clave == 7:
                                tname['Table Name'] = 'Epic Dragon Attacks'
                                tables.append(tname)
                                for index, elem in enumerate(claves):
                                    clean_elem = str(elem).replace(' ', '').replace('1', '1 ').replace('2', '2 ')
                                    tabla[clean_elem] = valores[index::len(claves)]
                            elif num_clave == 8:
                                tname['Table Name'] = 'Epic Dragon Breath Weapons'
                                tables.append(tname)
                                notes.append(valores[8])
                                del valores[8]
                                for index, elem in enumerate(claves):
                                    tabla[elem] = valores[index::len(claves)]
                            elif num_clave == 9:
                                tname['Table Name'] = 'Epic Dragon Overland Flying Speeds'
                                tables.append(tname)
                                while '' in claves:
                                    claves.remove('')
                                while '' in valores:
                                    valores.remove('')
                                tabla[str(claves[0]).replace('————— ', '').replace(' —————', '')] = claves[1:4]
                                tabla[claves[4] + valores[0]] = valores[1:4]
                                tabla[claves[4] + valores[4]] = valores[5:8]
                                tabla[claves[5] + valores[8]] = valores[9:12]
                            else:
                                for index, elem in enumerate(claves):
                                    tabla[elem] = valores[index::len(claves)]

                if tabla:
                    tables.append(tabla)
                    if notes:
                        notas = {}
                        for elem in notes:
                            notas['Notas'] = elem
                        tables.append(notas)
                        notes = []
        else:
            for index, elem in enumerated_data:
                tabla = {}
                if isinstance(elem, str):
                    if elem == 'CLAVES':
                        en_claves = True
                    elif elem == 'VALORES':
                        en_valor = True
                    else:
                        tabla['Table Name'] = str(elem)
                if isinstance(elem, list):
                    if en_claves:
                        claves = elem
                        num_clave += 1
                        en_claves = False
                    elif en_valor:
                        valores = elem
                        en_valor = False
                        if isinstance(self.initial_data[3], str):
                            for index, elem in enumerate(claves):
                                tabla[elem] = valores[index::len(claves)]
                if tabla:
                    tables.append(tabla)

        if tables:
            del self.initial_data[3:indexes]
            for elem in tables:
                self.initial_data.append(elem)


def checking_files(folder):
    CLAVES = {'Monstruo y Nivel', 'Size/Type', 'Hit Dice', 'Initiative', 'Speed', 'Armor Class',
              'Base Attack/Grapple', 'Attack', 'Full Attack', 'Space/Reach', 'Special Attacks', 'Special Qualities',
              'Saves', 'Abilities', 'Skills', 'Feats', 'Environment', 'Organization', 'Challenge Rating', 'Treasure',
              'Alignment', 'Advancement', 'Level Adjustment'}
    vacios = []
    sin_nombre = []
    sin_valor = []
    creatures = []
    sin_descripcion = []
    sv = {}
    for path in glob.glob('{}/*.json'.format(folder)):
        with open(path, 'r') as f:
            filename = os.path.basename(path)
            data = json.load(f)
            enumerated_data = enumerate(data)
            if not data:
                vacios.append(path)
            else:
                for index, elem in enumerated_data:
                    clean_keys = set()
                    if index == 0:
                        for key, val in elem.items():
                            if 'Nombre' in key:
                                pass
                            else:
                                sin_nombre.append(path)
                    if index == 1:
                        for key, val in elem.items():
                            if key:
                                clean_keys.add(key)
                            if not val:
                                filename = os.path.basename(path)
                                sin_valor.append(filename + ' ' + key)
                        if clean_keys != CLAVES:
                            print(os.path.basename(path) + ': No tiene todas las CLAVES')
                            claves_de_mas = clean_keys.difference(CLAVES)
                            if claves_de_mas:
                                print('Tiene las siguientes CLAVES de más: ')
                            print('Le faltan las siguientes CLAVES: ')
                            print(CLAVES.difference(clean_keys), '\n')
                    if index == 2:
                        for key, val in elem.items():
                            if key == 'Descripción':
                                if not val:
                                    print(filename)
                            else:
                                print('Mira este: ', filename)
                    if index == 3:
                        if isinstance(elem, str):
                            creatures.append(filename)
                        else:
                            pass
                    if index == 4:
                        if isinstance(elem, str):
                            print(filename, elem)
                        else:
                            pass
                    if index > 4:
                        pass

    if vacios:
        print('Los siguientes archivos están vacíos: ')
        for elem in vacios:
            print(elem)
    if sin_nombre:
        print('Las siguientes criaturas no tienen nombre: ')
        for elem in sin_nombre:
            print(elem)
    if sin_valor:
        print('Las siguientes criaturas no tienen valor en estas claves:')
        for elem in sin_valor:
            print(elem)
    if creatures:
        print('Las siguientes criaturas tienen el combate como descripción: ')
        for elem in creatures:
            print(elem)


def main():
    parser = argparse.ArgumentParser(description='Analiza los archivos html de dandwiki, y pasa las criaturas de '
                                                 '3.5 a archivos JSON.')

    parser.add_argument('-H', '--h_folder', type=str, help='Cambia el directorio donde se encontrará la carpeta '
                                                           'HTML con los archivos HTML')
    parser.add_argument('-J', '--j_folder', type=str, help='Cambia el directorio donde se encontrará la carpeta '
                                                           'JSON con los archivos JSON')
    parser.add_argument('-d', '--download', action='store_true', help='Descarga los ficheros HTML')
    parser.add_argument('-j', '--to_json', action='store_true', help='Convierte los ficheros HTML '
                                                                     'a JSON')
    parser.add_argument('-c', '--clean', action='store_true', help='Estructura todos los archivos JSON '
                                                                   'para que tengan el contenido '
                                                                   'definitivo')
    parser.add_argument('-ch', '--checking', action='store_true', help='Comprueba que tienen los archivos')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-q', '--quiet', action='store_true', help='Elimina los print que describen el proceso')
    group.add_argument('-v', '--verbose', action='store_true', help='print verbose')

    args = parser.parse_args()

    dir_path = os.path.normpath(os.getcwd())
    backup_folder = os.path.join(dir_path, '..', 'raw')
    hfolder = os.path.join(backup_folder, 'HTML')
    if args.h_folder:
        hfolder = os.path.normpath(args.h_folder)
    jfolder = os.path.join(backup_folder, 'JSON')
    if args.j_folder:
        jfolder = os.path.normpath(args.j_folder)
    tipos_folder = os.path.join(jfolder, 'TIPOS')
    dragon_folder = os.path.join(tipos_folder, 'DRAGONES')

    if args.download:
        if not os.path.isdir(hfolder):
            os.makedirs(hfolder)
        if args.quiet:
            dumper_html(hfolder)
        elif args.verbose:
            print('Se están recogiendo los archivos HTML...')
            dumper_html(hfolder, to_print=True)
            print('¡Proceso completado!' + '\n')
        else:
            print('Se están recogiendo los archivos HTML, por favor espere...')
            dumper_html(hfolder)
            print('¡Proceso completado!' + '\n')

    if args.to_json:
        if not os.path.isdir(jfolder):
            os.makedirs(jfolder)
        if args.quiet:
            to_json(hfolder, jfolder)
        elif args.verbose:
            print('Creando ficheros JSON...')
            to_json(hfolder, jfolder, to_print=True)
            print('¡Proceso completado!' + '\n')
        else:
            print('Se están recogiendo los archivos JSON, por favor espere...')
            to_json(hfolder, jfolder)
            print('¡Proceso completado!' + '\n')

    if args.clean:
        if not args.quiet:
        for path in glob.glob('{}/*.json'.format(jfolder)):
            cleaner = SRD35_JsonClean(path)
            cleaner.excluyendo_ficheros()
            cleaner.insertando_titulos()
            cleaner.organizando_tipos()
            cleaner.insertando_claves()
            cleaner.insertando_descripciones()
            cleaner.eliminando_entradas()
            cleaner.eliminando_back_to_main()
            cleaner.arreglando_tablas()
        for path in glob.glob('{}/*.json'.format(tipos_folder)):
            cleaner.arreglando_tablas_tipo()
        for path in glob.glob('{}/*.json'.format(dragon_folder)):
            cleaner.arreglando_tablas_dragones()

        elif args.verbose:
            print('Excluyendo ficheros innecesarios...')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).excluyendo_ficheros(to_print=True)
            print('¡Proceso completado!' + '\n')
            print('Insertando nombre a los siguientes archivos:')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).insertando_titulos(to_print=True)
            print('¡Proceso completado!' + '\n')
            print('Clasificando monstruos...')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).organizando_tipos(to_print=True)
            print('¡Proceso completado!' + '\n')
            print('Insertando "Monstruo y Nivel" en las tablas de los siguientes archivos:')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).insertando_claves(to_print=True)
            print('¡Proceso completado!' + '\n')
            print('Insertando "Descripción" a las criaturas que no tienen...')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).insertando_descripciones(to_print=True)
            print('¡Proceso completado!' + '\n')
            print('Eliminando algunas entradas que están vacías...')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).eliminando_entradas(to_print=True)
            print('¡Proceso completado!' + '\n')
            print('Retocando algunas entradas...')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).eliminando_back_to_main(to_print=True)
            print('¡Proceso completado!' + '\n')
            # print('Arreglando tablas...')
            # for path in glob.glob('{}/*.json'.format(jfolder)):
            #     SRD35_JsonClean(path).arreglando_tablas(to_print=True)
            # print('¡Proceso Completado!' + '\n')
            # print('Arreglando tablas en la carpeta TIPOS...')
            # for path in glob.glob('{}/*.json'.format(tipos_folder)):
            #     SRD35_JsonClean(path).arreglando_tablas_tipo(to_print=True)
            # print('¡Proceso Completado!' + '\n')
            # print('Arreglando tablas en la carpeta DRAGONES...')
            # for path in glob.glob('{}/*.json'.format(dragon_folder)):
            #     SRD35_JsonClean(path).arreglando_tablas_dragones(to_print=True)
            # print('¡Proceso Completado!' + '\n')

        else:
            print('Espere mientras se filtran y reeditan los archivos...')
            for path in glob.glob('{}/*.json'.format(jfolder)):
                SRD35_JsonClean(path).excluyendo_ficheros()
                SRD35_JsonClean(path).insertando_titulos()
                SRD35_JsonClean(path).organizando_tipos()
                SRD35_JsonClean(path).insertando_claves()
                SRD35_JsonClean(path).insertando_descripciones()
                SRD35_JsonClean(path).eliminando_entradas()
                SRD35_JsonClean(path).eliminando_back_to_main()
                SRD35_JsonClean(path).arreglando_tablas()
            for path in glob.glob('{}/*.json'.format(tipos_folder)):
                SRD35_JsonClean(path).arreglando_tablas_tipo()
            for path in glob.glob('{}/*.json'.format(dragon_folder)):
                SRD35_JsonClean(path).arreglando_tablas_dragones()
            print('¡Proceso Completado!' + '\n')

    if args.checking:
        print('Analizando archivos...')
        for path in glob.glob('{}/*.json'.format(tipos_folder)):
            SRD35_JsonClean(path).arreglando_tablas_tipo()
        print('¡Proceso Completado!' + '\n')


# TODO Arreglar el Combate del Balor.json... o no...

# TODO Hacer un parser que recoja los conjuros en condiciones

# TODO Arreglar las tablas extra en TIPOS y DRAGONES

# TODO Cambiar el Duergar.json y los cambiaformas para que recoga el valor del diccionario como una tabla

# TODO Traducir todas las claves
if __name__ == '__main__':
    main()
