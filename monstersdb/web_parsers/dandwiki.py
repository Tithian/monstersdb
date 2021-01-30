import os
import shutil
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
        self.temp_total_tables = []
        self.temp_total_rare_tables = []
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
                    if self.temp_description:
                        self.description['Descripción'] = self.temp_description
                        self.temp_description = ''
                    elif self.temp_rare_value:
                        self.description['Descripcion'] = self.temp_rare_value
                        self.temp_rare_value = ''
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

                elif self.in_h1:
                    if not self.temp_monster_name:
                        self.in_monster_name = True
                elif self.in_raro:
                    self.in_rare_description_key = True
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

                if self.temp_total_tables:
                    for elem in self.temp_total_tables:
                        self.monster.append(elem)
                    self.monster.append(self.description)

                if self.temp_combate:
                        self.temp_combate = self.temp_combate.replace('COMBAT', '')
                        self.temp_combate = self.temp_combate.replace('Combat', '')
                        self.monster.append(self.content)
                        if not self.content:
                            self.content['Combate'] = self.temp_combate

                if self.temp_rare_content:
                    self.monster.append(self.temp_rare_content)

                if self.temp_total_rare_tables:
                    for elem in self.temp_total_rare_tables:
                        self.monster.append(elem)

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
                self.temp_total_tables.append(self.temp_table)
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
                self.value_row = 0
                self.in_rare_table = False
                self.in_rare_table_value = False
                if self.temp_rare_table:
                    self.temp_total_rare_tables.append(self.temp_rare_table)
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
                    data = '-----' + data
                    self.temp_rare_table_key += data

        elif self.in_rare_table and self.in_rare_table_value:
            if 'This material is published under the ' in data:
                pass
            elif 'OGL' in data:
                pass
            else:
                data = data.replace(' ', '')
                if data:
                    data = '-----' + data
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


# class MultipleCreatureParser(HTMLParser):
#     def __init__(self, *arg, **kwargs):
#         super(MultipleCreatureParser, self).__init__(*arg, **kwargs)
#         # import ipdb; ipdb.set_trace()  # debugging manual
#
#         self.start = False
#         # Informacion
#         self.monster = []
#         self.monster_name = {}
#         self.total_principal_tables = {}
#         self.total_rare_tables = {}
#         self.table = {}
#         self.content = {}
#         self.description = {}
#         # Informacion Raros
#         self.rare_monster = {}
#         self.rare_content = {}
#         # Flags
#         self.in_table = False
#         self.in_key = False
#         self.in_value = False
#         self.in_combate = False
#         self.in_p = False
#         self.in_h1 = False
#         self.in_monster_name = False
#         self.start_document = False
#         self.start_description = False
#         self.in_description = False
#         self.finish_document = False
#         self.in_raro = False
#         self.in_rare_description_key = False
#         self.in_rare_value = False
#         self.in_rare_table = False
#         self.in_rare_table_value = False
#         self.in_rare_table_key = False
#         self.value_row = 0
#
#         # Temps
#         self.temp_total_tables = []
#         self.temp_total_rare_tables = []
#         self.temp_table = {}
#         self.temp_rare_table = {}
#         self.temp_rare_content = {}
#         self.temp_monster_name = ''
#         self.temp_key = ''
#         self.temp_value = ''
#         self.temp_combate = ''
#         self.temp_description = ''
#         self.temp_rare_description_key = ''
#         self.temp_rare_value = ''
#         self.temp_rare_table_key = ''
#         self.temp_rare_table_value = ''
#
#     def reset(self):
#         super(MultipleCreatureParser, self).reset()
#         self.monster = []
#         self.name = {}
#         self.table = {}
#         self.content = {}
#         self.description = {}
#         self.in_table = False
#         self.in_key = False
#         self.in_value = False
#         self.in_combate = False
#         self.in_p = False
#         self.in_h1 = False
#         self.start_document = False
#         self.start_description = False
#         self.in_description = False
#         self.finish_document = False
#         self.rare_monster = []
#         self.rare_content = {}
#         self.in_raro = False
#         self.in_rare_value = False
#
#
#     def handle_starttag(self, tag, attrs):
#         attrs = dict(attrs)
#         css = attrs.get('class', '')
#
#         if tag == 'div' and 'mw-body-content' in css:
#             self.start_document = True
#             print('Empezando a parsear...')
#             self.temp_description = ''
#             self.start_description = True
#
#         if self.start_document:
#             if tag == 'table':
#                 if 'monstats' in css:
#                     self.temp_table = {}
#                     self.in_table = True
#                     self.in_rare_table_value = False
#                 else:
#                     print('- Hay Una Tabla Rara -')
#                     self.temp_rare_table = {}
#                     self.in_description = False
#                     self.in_rare_table = True
#                     # self.in_raro = False
#
#             elif self.in_table:
#                 if tag == 'th':
#                     self.temp_key = ''
#                     self.in_key = True
#                 if tag == 'td':
#                     self.temp_value = ''
#                     self.in_value = True
#             if self.in_rare_table:
#                 if tag == 'th':
#                     # self.in_rare_table_value = False
#                     self.in_rare_table_key = True
#                 if tag == 'td':
#                     # self.temp_rare_table_value = ''
#                     self.in_rare_table_value = True
#
#             if tag == 'h1':
#                 self.in_h1 = True
#             if tag == 'h2':
#                 self.in_h1 = False
#                 self.in_description = False
#                 self.in_raro = True
#             if tag == 'h3':
#                 h3_id = attrs.get('id', '')
#                 self.in_h1 = False
#                 self.in_description = False
#                 self.in_raro = True
#                 if self.temp_rare_description_key:
#                     self.temp_rare_content[self.temp_rare_description_key] = self.temp_rare_value
#                 elif 'siteSub' in h3_id:
#                     self.in_raro = False
#
#
#             elif tag == 'span' and 'headline' in css:
#                 id_span = attrs.get('id', '').capitalize()
#                 if 'Combat' in id_span:
#                     if self.temp_description:
#                         self.description['Descripción'] = self.temp_description
#                         self.temp_description = ''
#                     elif self.temp_rare_value:
#                         self.description['Descripcion'] = self.temp_rare_value
#                         self.temp_rare_value = ''
#                     self.start_description = False
#                     self.in_description = False
#                     self.in_raro = False
#                     self.in_combate = True
#
#                 elif 'Elemental' in id_span:
#                     self.in_raro = False
#                     self.in_description = True
#                 elif 'See' in id_span:
#                     self.start_description = False
#                     self.in_combate = False
#                 elif 'characters' in id_span:
#                     self.start_description = False
#                     self.in_combate = False
#                 elif 'S' in id_span:
#                     self.in_description = False
#                     self.in_combate = False
#
#                 elif self.in_h1:
#                     if not self.temp_monster_name:
#                         self.in_monster_name = True
#                 elif self.in_raro:
#                     self.in_rare_description_key = True
#                     if self.temp_rare_description_key:
#                         self.temp_rare_value = ''
#                         self.temp_rare_description_key = ''
#                         # self.in_raro = True
#
#
#             elif self.in_raro and tag == 'p':
#                 self.start_description = False
#                 self.in_rare_value = True
#
#                 #print(self.temp_rare_value)
#
#             elif tag == 'hr':
#                 if self.monster_name:
#                     self.monster.append(self.monster_name)
#
#                 if self.temp_total_tables:
#                     for elem in self.temp_total_tables:
#                         self.monster.append(elem)
#                     self.monster.append(self.description)
#
#                 if self.temp_combate:
#                         self.temp_combate = self.temp_combate.replace('COMBAT', '')
#                         self.temp_combate = self.temp_combate.replace('Combat', '')
#                         self.monster.append(self.content)
#                         if not self.content:
#                             self.content['Combate'] = self.temp_combate
#
#                 if self.temp_rare_content:
#                     self.monster.append(self.temp_rare_content)
#
#                 if self.temp_total_rare_tables:
#                     for elem in self.temp_total_rare_tables:
#                         self.monster.append(elem)
#
#                 self.start_document = False
#
#             elif self.start_description and tag == 'p':
#                 self.in_description = True
#
#     def handle_endtag(self, tag):
#         if self.in_monster_name and tag == 'h1':
#             self.in_h1 = False
#             if self.temp_monster_name:
#                 self.monster_name['Nombre'] = self.temp_monster_name.capitalize()
#             self.in_monster_name = False
#
#         elif self.in_table:
#             if tag == 'table':
#                 self.in_table = False
#                 self.temp_total_tables.append(self.temp_table)
#                 self.temp_table = {}
#                 # self.temp_combate = '' #comprobar si esta línea sirve para algo
#             elif self.in_key and tag == 'th':
#                 self.in_key = False
#             elif self.in_value and tag == 'td':
#                 self.in_value = False
#
#             elif tag == 'tr':
#                 if self.temp_key.endswith(':'):
#                     self.temp_key = self.temp_key[:-1]
#                     self.temp_table[self.temp_key] = self.temp_value
#                     self.temp_key = ''
#                     self.temp_value = ''
#                 else:
#                     self.temp_table['Monstruo y Nivel'] = self.temp_key
#
#         elif self.in_rare_table:
#             if tag == 'table':
#                 self.value_row = 0
#                 self.in_rare_table = False
#                 self.in_rare_table_value = False
#                 if self.temp_rare_table:
#                     self.temp_total_rare_tables.append(self.temp_rare_table)
#             elif tag == 'tr':
#                 if self.in_rare_table_key:
#                     self.temp_rare_table['Columnas'] = self.temp_rare_table_key
#                     self.in_rare_table_key = False
#                     self.temp_rare_table_key = ''
#                 elif self.in_rare_table_value:
#                     if self.temp_rare_table_value:
#                         self.value_row += 1
#                         self.temp_rare_table['Fila ' + str(self.value_row)] = self.temp_rare_table_value
#                         self.temp_rare_table_value = ''
#                         self.in_rare_table_value = False
#
#         elif self.in_raro and tag == 'h3':
#             self.in_rare_description_key = False
#
#         elif self.in_rare_value and tag == 'p':
#             self.in_rare_value = False
#
#
#     def handle_data(self, data):
#         data = data.replace('\n', '')
#         #En la Abominación me pilla una cantidad de espacios enormes, esta es la única solución que se de momento
#         data = data.replace('                            ', ' ')
#         data = data.replace('                        ', ' ')
#         data = data.replace('     ', ' ')
#
#         if self.in_table and self.in_key:
#             self.temp_key += data
#         elif self.in_table and self.in_value:
#             self.temp_value += data
#
#         elif self.in_rare_table and self.in_rare_table_key:
#             if '# of ' in data:
#                 pass
#             else:
#                 data = data.replace(' ', '')
#                 if data:
#                     data = '-----' + data
#                     self.temp_rare_table_key += data
#
#         elif self.in_rare_table and self.in_rare_table_value:
#             if 'This material is published under the ' in data:
#                 pass
#             elif 'OGL' in data:
#                 pass
#             else:
#                 data = data.replace(' ', '')
#                 if data:
#                     data = '-----' + data
#                     self.temp_rare_table_value += data
#
#         elif self.in_monster_name:
#             self.temp_monster_name += data
#
#         elif self.in_combate:
#             self.temp_combate += data
#
#         elif self.in_description:
#             self.temp_description += data
#
#         elif self.in_rare_description_key:
#             self.temp_rare_description_key += data
#         elif self.in_rare_value:
#             self.temp_rare_value += data


def parse_url(parser, url):
    response = requests.get(url)
    if response.status_code == 200:
        parser.feed(response.text)


def dumper_html(folder):
    """
    Esta función vuelca el contenido de los html a un directorio
    """
    print('Se están recogiendo los siguientes HTML: ')


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
        html_folder = os.path.join(folder, 'HTML')
        if not os.path.isdir(html_folder):  # Si el directorio pasado como argumento no existe:
            os.mkdir(html_folder)  # Crea el directorio pasado como argumento
        filename = os.path.join(html_folder, filename)
        with open(filename, 'wb') as f:
            print(filename)
            f.write(response.content)
    print('¡Proceso completado!')

def html2jsondumper(folder):
    print('Creando ficheros JSON...')
    for path in glob.glob('{}\*.html'.format(folder)):
        parser = SRD35_HTMLParser()
        with open(path, 'r+', encoding='utf-8') as f1:
            parser.feed(f1.read())
            response = json.dumps(parser.monster, indent=2)
            json_folder = os.path.join(folder, '../JSON')
            if not os.path.isdir(json_folder):  # Si el directorio pasado como argumento no existe:
                os.mkdir(json_folder)  # Crea el directorio pasado como argumento
            filename = os.path.basename(path)
            filename = os.path.join(json_folder, filename)
            with open(filename.replace('.html', '.json'), 'w') as f2:
                print(filename)
                f2.write(response)
    print('¡Proceso Completado!')

# def multiplecreatures2jsondumper(folder):
#     print('Creando ficheros JSON...')
#     for path in glob.glob('{}\Air_Elemental.html'.format(folder)):
#         parser = MultipleCreatureParser()
#         with open(path, 'r+', encoding='utf-8') as f1:
#             parser.feed(f1.read())
#             response = json.dumps(parser.monster, indent=2)
#             json_folder = os.path.join(folder, '../JSON')
#             if not os.path.isdir(json_folder):  # Si el directorio pasado como argumento no existe:
#                 os.mkdir(json_folder)  # Crea el directorio pasado como argumento
#             filename = os.path.basename(path)
#             filename = os.path.join(json_folder, filename)
#             print(filename)
#             print(response)
#             with open(filename.replace('.html', '.json'), 'w') as f2:
#                 print(filename)
#                 # f2.write(response)
#     print('¡Proceso Completado!')

def excluyendo_ficheros(folder):
    '''Compara el primer diccionario para ver si tiene claves útiles, los archivos que no las tengan son movidos
    al directorio EXCLUDED. Salvo 3 excepciones, Demon, Devil y Dire_Animal'''
    print('Los siguientes ficheros han sido movidos a la carpeta EXCLUDED: ')
    files_to_exclude = []
    for path in glob.glob('{}/*.json'.format(folder)):
            with open(path, 'r+') as f:
                data = json.load(f)
                found = False
                if 'Demon' in path:
                    found = True
                if 'Devil' in path:
                    found = True
                if 'Dire_Animal' in path:
                    found = True
                enumerated_data = enumerate(data)
                for index, dictionary in enumerated_data:
                    # print(item)
                    if index == 0:
                        for key, val in dictionary.items():
                            if 'Nombre' in key:
                                found = True
                                if 'Cr 1/10' in val:
                                    found = False
                                if 'Creatures by type' in val:
                                    found = False
                                if 'Creature types and subtypes' in val:
                                    found = False
                                # print(key)
                            if 'Monstruo y Nivel' in key:
                                found = True
                            if 'Size/Type' in key:
                                found = True
                            if 'Descripción' in key:
                                found = True
                            if 'Combate' in key:
                                found = True
                    if index != 0:
                        pass
                if not found:
                    filename = (os.path.realpath(path))
                    excluded_folder = os.path.join(folder, '..\EXCLUDED')
                    if not os.path.isdir(excluded_folder):  # Si el directorio pasado como argumento no existe:
                        os.mkdir(excluded_folder)  # Crea el directorio pasado como argumento
                    shutil.copy2(filename, excluded_folder)
                    files_to_exclude.append(filename)
                    print(filename)
                    f.close()
                    os.remove(filename)
    print('¡Proceso Completado!')


def insertando_titulos(folder):
    print('Añadiendo Títulos a las criaturas que no tienen...')
    for path in glob.glob('{}/*.json'.format(folder)):
        with open(path, 'r+') as f:
            data = json.load(f)
            name_found = False
            enumerated_data = enumerate(data)
            for index, elem in enumerated_data:
                if index != 0:
                    pass
                if index == 0:
                    for key, val in elem.items():
                        if 'Nombre' in key:
                            name_found = True
                        else:
                            pass
                    if not name_found:
                        with open(path, 'w') as f2:
                            new_index = {}
                            old_name = os.path.basename(path.replace('.json', ''))
                            new_name = '{}'.format(old_name.replace('_', ' '))
                            new_index['Nombre'] = new_name
                            data.insert(0, new_index)
                            response = json.dumps(data, indent=2)
                            f2.write(response)
    print('¡Proceso completado!')


def organizando_tipos(folder):
    print('Los siguientes ficheros son tipos de monstruos. Clasificando...:')
    files_to_exclude = []
    tipos_folder = os.path.join(folder, 'TIPOS')
    dragon_folder = os.path.join(tipos_folder, 'DRAGONES' )
    if not os.path.isdir(dragon_folder):  # Si el directorio pasado como argumento no existe:
         os.makedirs(dragon_folder)  # Crea el directorio pasado como argumento
    for path in glob.glob('{}/*.json'.format(folder)):
        with open(path, 'r+') as f:
            criatura_tipo = False
            data = json.load(f)
            enumerated_data = enumerate(data)
            for index, elem in enumerated_data:
                if index != 1:
                    pass
                if index == 1:
                    for key, val in elem.items():
                        if 'Monstruo y Nivel' in key:
                            criatura_tipo = True
                            # print(val)
                        if 'Size/Type' in key:
                            criatura_tipo = True
                        else:
                            pass
            if not criatura_tipo:
                filename = (os.path.realpath(path))
                shutil.copy2(filename, tipos_folder)
                files_to_exclude.append(filename)
                print(filename)
                f.close()
                os.remove(filename)
    print('Los siguientes archivos son Dragones: ')
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
            else:
                for index, elem in enumerated_data:
                    for key, val in elem.items():
                        if 'dragon' in val.lower():
                            is_dragon = True
                if is_dragon:
                        filename = (os.path.realpath(path))
                        shutil.copy2(filename, dragon_folder)
                        print(filename)
                        f.close()
                        os.remove(filename)
    print('¡Proceso Completado!')


def checking_files(folder):
    CLAVES = {'Monstruo y Nivel', 'Size/Type', 'Hit Dice', 'Initiative', 'Speed', 'Armor Class',
              'Base Attack/Grapple', 'Attack', 'Full Attack', 'Space/Reach', 'Special Attacks', 'Special Qualities',
              'Saves', 'Abilities', 'Skills', 'Feats', 'Environment', 'Organization', 'Challenge Rating', 'Treasure',
              'Alignment', 'Advancement', 'Level Adjustment'}
    print('')
    for path in glob.glob('{}/*.json'.format(folder)):
        with open(path, 'r') as f:
            data = json.load(f)
            enumerated_data = enumerate(data)
            for index, elem in enumerated_data:
                clean_keys = set()
                if index != 1:
                    pass
                if index == 1:
                    for key, val in elem.items():
                        if val:
                            clean_keys.add(key)
                    if clean_keys != CLAVES:
                        print(os.path.basename(path) + ': No tiene todas las CLAVES')
                        print('Tiene las siguientes CLAVES de más: ')
                        print(clean_keys.difference(CLAVES))
                        print('Le faltan las siguientes CLAVES: ')
                        print(CLAVES.difference(clean_keys))

    print('¡Proceso Completado!')


def main():
    dir_path = os.path.dirname(os.getcwd())
    os.path.normpath(dir_path)
    backup_folder = os.path.join(dir_path, 'raw')
    html_folder = os.path.join(backup_folder, 'HTML')
    json_folder = os.path.join(backup_folder, 'JSON')

    dumper_html(backup_folder) # PASO 1 - Volcar el contenido Html
    html2jsondumper(html_folder) # PASO 2 - Transformar el contenido Html a Json
    excluyendo_ficheros(json_folder) # PASO 3 - Excluir los ficheros que no sirven
    insertando_titulos(json_folder) # PASO 4 - Insertando titulos en los ficheros que no tienen
    organizando_tipos(json_folder) # PASO 5 - Pone todos los monstruos que sean un tipo en un directorio y los dragones en una carpeta a parte

    #checking_files(json_folder) #TODO PASO 6 - Chequear todos las claves y valores de las tablas

    # multiplecreatures2jsondumper(html_folder)

    # backup_folder = Path('/monstersdb/monstersdb/raw')


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
"""
Clases de victor para usar os.path:
dir_path = os.path.dirname(os.path.realpath(_file_))
    backup_folder = os.path.join(dir_path, '..', 'raw')
os.path.join(dir_path, '.../raw')
"""
"""
    

"""
if __name__ == '__main__':
    main()
