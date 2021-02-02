import os
import shutil
import json
import glob
from html.parser import HTMLParser

import requests


class NameParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(NameParser, self).__init__(*arg, **kwargs)
        self.start = False
        self.monster_name = {}
        self.temp_monster_name = ''
        self.in_monster_name = False

    def reset(self):
        super(NameParser, self).reset()
        self.monster_name = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'div' and 'mw-body-content' in css:
            self.start = True

        if self.start:
            if tag == 'h1':
                if not self.temp_monster_name:
                    self.in_monster_name = True

    def handle_endtag(self, tag):
        if self.in_monster_name and tag == 'h1':
            self.monster_name['Nombre'] = self.temp_monster_name.capitalize()
            self.in_monster_name = False

        if tag == 'hr':
            self.start = False

    def handle_data(self, data):
        while '  ' in data:
            data = data.replace('  ', ' ')

        if self.in_monster_name:
            self.temp_monster_name += data


class TableParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(TableParser, self).__init__(*arg, **kwargs)
        self.start = False
        # Informacion
        self.total_principal_tables = []
        self.table = {}
        # Flags
        self.in_table = False
        self.in_key = False
        self.in_value = False
        # Temps
        self.temp_table = {}
        self.temp_key = ''
        self.temp_value = ''

    def reset(self):
        super(TableParser, self).reset()
        self.table = {}
        self.in_table = False
        self.in_key = False
        self.in_value = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'div' and 'mw-body-content' in css:
            self.start = True

        if self.start:
            if tag == 'table':
                if 'monstats' in css:
                    self.temp_table = {}
                    self.in_table = True

            elif self.in_table:
                if tag == 'th':
                    self.temp_key = ''
                    self.in_key = True
                if tag == 'td':
                    self.temp_value = ''
                    self.in_value = True

    def handle_endtag(self, tag):
        if self.in_table:
            if tag == 'table':
                self.in_table = False
                self.total_principal_tables.append(self.temp_table)
                self.temp_table = {}
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

        elif tag == 'hr':
            self.start = False

    def handle_data(self, data):
        while '  ' in data:
            data = data.replace('  ', ' ')
        if self.in_table:
            data = data.replace('\n', '')
            if self.in_key:
                self.temp_key += data
            elif self.in_value:
                self.temp_value += data


class DescriptionParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(DescriptionParser, self).__init__(*arg, **kwargs)
        self.start = False
        self.content = {}
        self.description = {}
        self.start_description = False
        self.in_description = False
        self.in_toc = False
        self.in_h1 = False
        self.in_h2 = False
        self.temp_description = ''

    def reset(self):
        super(DescriptionParser, self).reset()
        self.content = {}
        self.description = {}
        self.in_toc = False
        self.in_h1 = False
        self.in_h2 = False
        self.start_description = False
        self.in_description = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'div' and 'mw-body-content' in css:
            self.start = True
            self.temp_description = ''
        if tag == 'div' and 'toc' in css:
            self.in_toc = True
        if tag == 'h2':
            self.in_h2 = True
        if tag == 'h1':
            self.in_h1 = True
        if tag == 'span':
            self.in_description = False

        elif self.start:
            if not self.in_toc or not self.in_h2 or not self.in_h1:
                if tag == 'table':
                    self.in_description = False

                elif tag == 'p':
                    self.in_description = True
#  He cambiado algo aquí, estar atento por si falla al tomar la descripción
                elif tag == 'h3':
                    h3_id = attrs.get('id', '')
                    self.start = False
                    if 'siteSub' in h3_id:
                        self.start = True

    def handle_endtag(self, tag):
        if tag == 'hr':
            clean_descr = self.temp_description.replace('\n\n', '')
            if clean_descr:
                if clean_descr.startswith('\n', 0, 4):
                    self.description['Descripción'] = clean_descr.replace('\n', '', 1)
                    self.temp_description = ''
                else:
                    self.description['Descripción'] = clean_descr
                    self.temp_description = ''
            self.start = False
            self.start_description = False
            self.in_description = False
        if self.in_toc:
            if tag == 'div':
                self.in_toc = False

    def handle_data(self, data):
        while '  ' in data:
            data = data.replace('  ', ' ')

        if self.start:
            if self.in_description:
                self.temp_description += data


class CombatParser(HTMLParser):
    def __init__(self, *arg, **kwargs):
        super(CombatParser, self).__init__(*arg, **kwargs)
        self.start = False
        self.combat = {}
        self.in_combat = False
        self.temp_combat = ''

    def reset(self):
        super(CombatParser, self).reset()
        self.combat = {}
        self.in_combat = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = attrs.get('class', '')

        if tag == 'div' and 'mw-body-content' in css:
            self.start = True

        if self.start:
            if tag == 'span' and 'headline' in css:
                id_span = attrs.get('id', '').capitalize()
                if 'Combat' in id_span:
                    self.in_combat = True

                elif 'See' in id_span:
                    self.in_combat = False
                elif 'characters' in id_span:
                    self.in_combat = False
                elif 'S' in id_span:
                    self.in_combat = False

            elif tag == 'hr':
                while '\n\n\n' in self.temp_combat:
                    self.temp_combat = self.temp_combat.replace('\n\n\n', '\n\n')
                if self.temp_combat:
                    self.temp_combat = self.temp_combat.replace('\n\n', '')
                    if not self.combat:
                        if self.temp_combat.startswith('Combat', 0, 6):
                            clean_comb = self.temp_combat.replace('Combat', '', 1)
                            if clean_comb.startswith('\n', 0, 2):
                                clean_comb = clean_comb.replace('\n', '', 1)
                                self.combat['Combate'] = clean_comb
                        elif self.temp_combat.startswith('COMBAT', 0, 6):
                            clean_comb = self.temp_combat.replace('COMBAT', '', 1)
                            if clean_comb.startswith('\n', 0, 2):
                                clean_comb = clean_comb.replace('\n', '', 1)
                                self.combat['Combate'] = clean_comb
                    else:
                        self.combat['Combate'] = self.temp_combat

                self.start = False

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        while '  ' in data:
            data = data.replace('  ', ' ')

        if self.in_combat:
            self.temp_combat += data


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
    print('Se están recogiendo los siguientes HTML: ')
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
        name = path[path.rfind(':')+1:]
        # Le da formato al interior del placeholder {} con unacadena fuyo formato es igual a la variable nombre
        # reemplazando los espacios por guiones bajos
        filename = '{}.html'.format(name.replace(' ', '_'))

        response = requests.get('https://www.dandwiki.com{}'.format(path))
        html_folder = os.path.join(folder, 'HTML')
        if not os.path.isdir(html_folder):
            os.mkdir(html_folder)
        filename = os.path.join(html_folder, filename)
        with open(filename, 'wb') as f:
            print(filename)
            f.write(response.content)
    print('¡Proceso completado!')


def html2jsondumper(folder):
    print('Creando ficheros JSON...')
    for path in glob.glob(os.path.join(folder, '*.html')):
        parser = CombatParser()
        with open(path, 'r+', encoding='utf-8') as f1:
            parser.feed(f1.read())
            response = json.dumps(parser.combat, indent=2)
            json_folder = os.path.join(folder, '../JSON')
            if not os.path.isdir(json_folder):  # Si el directorio pasado como argumento no existe:
                os.mkdir(json_folder)  # Crea el directorio pasado como argumento
            filename = os.path.basename(path)
            filename = os.path.join(json_folder, filename)
            with open(filename.replace('.html', '.json'), 'w') as f2:
                print(filename)
                print(response)
                # f2.write(response)
    print('¡Proceso Completado!')


#  He tocado aquí, estar atento por si cambia algo
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
    dragon_folder = os.path.join(tipos_folder, 'DRAGONES')
    if not os.path.isdir(dragon_folder):
        os.makedirs(dragon_folder)
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
    # PASO 1 - Volcar el contenido Html
    # dumper_html(backup_folder)
    # PASO 2 - Transformar el contenido Html a Json
    html2jsondumper(html_folder)
    # PASO 3 - Excluir los ficheros que no sirven
    # excluyendo_ficheros(json_folder)
    # PASO 4 - Insertando titulos en los ficheros que no tienen
    # insertando_titulos(json_folder)
    # PASO 5 - Pone todos los monstruos que sean un tipo en un directorio y los dragones en una carpeta a parte
    # organizando_tipos(json_folder)

    # checking_files(json_folder)  #TODO PASO 6 - Chequear todos las claves y valores de las tablas

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
if __name__ == '__main__':
    main()
