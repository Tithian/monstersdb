import os
import json
import glob
from pathlib import Path
from html.parser import HTMLParser

import requests


class SRD35_HTMLParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(SRD35_HTMLParser, self).__init__(*arg, **kwargs)
        # import ipdb; ipdb.set_trace()  # debugging manual

        self.start = False
        # Informacion
        self.monster = []
        self.monster_name = {}
        self.total_principal_tables = {}
        self.total_rare_tables = {}
        self.table = {}
        self.content = {}
        self.description = {}
        # Informacion Raros
        self.rare_monster = {}
        self.rare_content = {}
        # Flags
        self.in_table = False
        self.in_key = False
        self.in_value = False
        self.in_combate = False
        self.in_p = False
        self.in_h1 = False
        self.in_monster_name = False
        self.start_document = False
        self.start_description = False
        self.in_description = False
        self.finish_document = False
        self.in_raro = False
        self.in_rare_description_key = False
        self.in_rare_value = False
        self.in_rare_table = False
        self.in_rare_table_value = False
        self.in_rare_table_key = False
        self.value_row = 0

        # Temps
        self.temp_table = {}
        self.temp_rare_table = {}
        self.temp_rare_content = {}
        self.temp_monster_name = ''
        self.temp_key = ''
        self.temp_value = ''
        self.temp_combate = ''
        self.temp_description = ''
        self.temp_rare_description_key = ''
        self.temp_rare_value = ''
        self.temp_rare_table_key = ''
        self.temp_rare_table_value = ''

    def reset(self):
        super(SRD35_HTMLParser, self).reset()
        self.monster = []
        self.name = {}
        self.table = {}
        self.content = {}
        self.description = {}
        self.in_table = False
        self.in_key = False
        self.in_value = False
        self.in_combate = False
        self.in_p = False
        self.in_h1 = False
        self.start_document = False
        self.start_description = False
        self.in_description = False
        self.finish_document = False
        self.rare_monster = []
        self.rare_content = {}
        self.in_raro = False
        self.in_rare_value = False


    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'div' and 'mw-body-content' in css:
            self.start_document = True
            self.temp_description = ''
            self.start_description = True

        if self.start_document:
            if tag == 'table':
                if 'monstats' in css:
                    self.temp_table = {}
                    self.in_table = True
                    self.in_rare_table_value = False
                else:
                    self.temp_rare_table = {}
                    self.in_description = False
                    self.in_rare_table = True
                    # self.in_raro = False

            elif self.in_table:
                if tag == 'th':
                    self.temp_key = ''
                    self.in_key = True
                if tag == 'td':
                    self.temp_value = ''
                    self.in_value = True
            if self.in_rare_table:
                if tag == 'th':
                    # self.in_rare_table_value = False
                    self.in_rare_table_key = True
                if tag == 'td':
                    # self.temp_rare_table_value = ''
                    self.in_rare_table_value = True

            if tag == 'h1':
                self.in_h1 = True
            if tag == 'h2':
                self.in_h1 = False
                self.in_description = False
                self.in_raro = True
            if tag == 'h3':
                h3_id = attrs.get('id', '')
                self.in_h1 = False
                self.in_description = False
                self.in_raro = True
                if self.temp_rare_description_key:
                    self.temp_rare_content[self.temp_rare_description_key] = self.temp_rare_value
                elif 'siteSub' in h3_id:
                    self.in_raro = False


            elif tag == 'span' and 'headline' in css:
                id_span = attrs.get('id', '').capitalize()
                if 'Combat' in id_span:
                    self.start_description = False
                    self.in_description = False
                    self.in_raro = False
                    self.in_combate = True

                elif 'Elemental' in id_span:
                    self.in_raro = False
                    self.in_description = True
                elif 'See' in id_span:
                    self.start_description = False
                    self.in_combate = False
                elif 'characters' in id_span:
                    self.start_description = False
                    self.in_combate = False
                elif 'S' in id_span:
                    self.in_description = False
                    self.in_combate = False
                elif 'Elemental' in id_span:
                    self.in_raro = False

                elif self.in_h1:
                    if not self.temp_monster_name:
                        self.in_monster_name = True
                elif self.in_raro:
                    self.in_rare_description_key = True
                    #     #Aqui se añade al diccionario rare_content
                    if self.temp_rare_description_key:
                        self.temp_rare_value = ''
                        self.temp_rare_description_key = ''
                        # self.in_raro = True


            elif self.in_raro and tag == 'p':
                self.start_description = False
                self.in_rare_value = True

                #print(self.temp_rare_value)

            elif tag == 'hr':
                if self.monster_name:
                    self.monster.append(self.monster_name)

                if self.total_principal_tables:
                    self.monster.append(self.total_principal_tables)

                if self.temp_description:
                    self.description['Descripción'] = self.temp_description
                    self.monster.append(self.description)

                if self.temp_combate:
                        self.temp_combate = self.temp_combate.replace('COMBAT', '')
                        self.temp_combate = self.temp_combate.replace('Combat', '')
                        self.monster.append(self.content)
                        if not self.content:
                            self.content['Combate'] = self.temp_combate

                if self.temp_rare_content:
                    self.monster.append(self.temp_rare_content)

                if self.total_rare_tables:
                    self.monster.append(self.total_rare_tables)

                self.start_document = False

            elif self.start_description and tag == 'p':
                self.in_description = True

    def handle_endtag(self, tag):
        if self.in_monster_name and tag == 'h1':
            self.in_h1 = False
            if self.temp_monster_name:
                self.monster_name['Nombre'] = self.temp_monster_name.capitalize()
            self.in_monster_name = False

        elif self.in_table:
            if tag == 'table':
                self.in_table = False
                self.total_principal_tables.update(self.temp_table)
                self.temp_table = {}
                # self.temp_combate = '' #comprobar si esta línea sirve para algo
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
                else:
                    self.temp_table['Monstruo y Nivel'] = self.temp_key

        elif self.in_rare_table:
            if tag == 'table':
                self.in_rare_table = False
                self.in_rare_table_value = False
                if self.temp_rare_table:
                    self.total_rare_tables.update(self.temp_rare_table)
                    self.temp_rare_table = {}
            elif tag == 'tr':
                if self.in_rare_table_key:
                    self.temp_rare_table['Columnas'] = self.temp_rare_table_key
                    self.in_rare_table_key = False
                    self.temp_rare_table_key = ''
                elif self.in_rare_table_value:
                    if self.temp_rare_table_value:
                        self.value_row += 1
                        self.temp_rare_table['Fila ' + str(self.value_row)] = self.temp_rare_table_value
                        self.temp_rare_table_value = ''
                        self.in_rare_table_value = False

        elif self.in_raro and tag == 'h3':
            self.in_rare_description_key = False

        elif self.in_rare_value and tag == 'p':
            self.in_rare_value = False


    def handle_data(self, data):
        data = data.replace('\n', '')
        #En la Abominación me pilla una cantidad de espacios enormes, esta es la única solución que se de momento
        data = data.replace('                            ', ' ')
        data = data.replace('                        ', ' ')
        data = data.replace('     ', ' ')

        if self.in_table and self.in_key:
            self.temp_key += data
        elif self.in_table and self.in_value:
            self.temp_value += data

        elif self.in_rare_table and self.in_rare_table_key:
            if '# of ' in data:
                pass
            else:
                data = data.replace(' ', '')
                if data:
                    data = '/' + data
                    self.temp_rare_table_key += data

        elif self.in_rare_table and self.in_rare_table_value:
            if 'This material is published under the ' in data:
                pass
            elif 'OGL' in data:
                pass
            else:
                data = data.replace(' ', '')
                if data:
                    data = '/' + data
                    self.temp_rare_table_value += data

        elif self.in_monster_name:
            self.temp_monster_name += data

        elif self.in_combate:
            self.temp_combate += data

        elif self.in_description:
            self.temp_description += data

        elif self.in_rare_description_key:
            self.temp_rare_description_key += data
        elif self.in_rare_value:
            self.temp_rare_value += data


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

def dumper_html(folder):
    """
    Esta función vuelca el contenido de los html a un directorio
    """

    if not os.path.isdir(folder): # Si el directorio pasado como argumento no existe:
        os.mkdir(folder) # Crea el directorio pasado como argumento

    parser = ListCreaturesHTMLParser() # Llama a la función que coge los enlaces de cada criatura
    url = 'https://www.dandwiki.com/wiki/Creatures' # Enlace donde están todos los enlaces de las criaturas
    parse_url(parser, url) # Llama a la función que chequea con el parser indicado la url indicada (ambos arriba)

    for path in parser.list_creatures: # Por cada enlace que tenga el parser:
        name = path[path.rfind(':')+1:] # Hace que el nombre sea igual a la dirección del enlace,
                                        # pero solo el texto a partir de los ':'

        filename = '{}.html'.format(name.replace(' ', '_')) # Le da formato al interior del placeholder {} con una
                                                            # cadena fuyo formato es igual a la variable nombre
                                                            # reemplazando los espacios por guiones bajos

        response = requests.get('https://www.dandwiki.com{}'.format(path))
        filename = os.path.join(folder, filename)
        with open(filename, 'wb') as f:
            print(filename)
            f.write(response.content)


def html2jsondumper(folder):
    for path in glob.glob('{}/*.html'.format(folder)):
        parser = SRD35_HTMLParser()
        with open(path, 'r', encoding='utf-8') as f1:
            parser.feed(f1.read())
            response = json.dumps(parser.monster)
            print(os.path.basename(path))
            print(response)

            with open(path.replace('.html', '.json'), 'w') as f2:
                f2.write(response)
                print(os.path.basename(path))
                print(response)

def checking_all_files(folder):
    CLAVES = {'Nombre', 'Monstruo y Nivel', 'Size/Type', 'Hit Dice', 'Initiative', 'Speed', 'Armor Class',
              'Base Attack/Grapple', 'Attack', 'Full Attack', 'Space/Reach', 'Special Attacks', 'Special Qualities',
              'Saves', 'Abilities', 'Skills', 'Feats', 'Environment', 'Organization', 'Challenge Rating', 'Treasure',
              'Alignment', 'Advancement', 'Level Adjustment', 'Descripción', 'Combate'}

    for path in glob.glob('{}/*.json'.format(folder)):
        with open(path) as f:
            data = json.load(f)
            found = False
            enumerated_data = enumerate(data)
            # print(type(enumerated_data))
            # print(list(enumerated_data))
            for dict, line in enumerated_data:
                # print(item)
                if dict == 0:
                    for key, val in line.items():
                        if 'Nombre' in key:
                            found = True
                            # print(key)
                        if 'Monstruo y Nivel' in key:
                            found = True
                        if 'Size/Type' in key:
                            found = True
                        if 'Descripción' in key:
                            found = True
                        if 'Combate' in key:
                            found = True
            if not found:
                print(os.path.basename(path))


def main():
    # html2jsondumper(Path('/monstersdb/monstersdb/raw'))
    checking_all_files(Path('/monstersdb/monstersdb/raw'))
    # backup_folder = Path('/monstersdb/monstersdb/raw')
    # dumper_html(backup_folder)

"""
RECOGE ARCHIVOS
def get_all_files(backup_folder):
    filename_list = []

    file_iterator = backup_folder.iterdir()

    for entry in file_iterator: # Meter .with_name('Nombre_del_archivo.html') tras entry
        if entry.is_file():
            # print(entry.name)
            filename_list.append(entry.name)

    return filename_list
"""
if __name__ == '__main__':
    main()
