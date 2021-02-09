import os
import shutil
import json
import glob
from html.parser import HTMLParser

import requests
import argparse


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


class TableParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(TableParser, self).__init__(*arg, **kwargs)
        # Informacion
        self.final_data = []
        self.table = {}
        # Flags
        self.in_table = False
        self.in_key = False
        self.in_value = False
        # Temps
        self.temp_table = {}
        self.temp_key = ''
        self.temp_value = ''

    def handle_starttag(self, tag, attrs):
        super(TableParser, self).handle_starttag(tag, attrs)
        if self.start:
            attrs = dict(attrs)
            css = attrs.get('class', '')

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
        super(TableParser, self).handle_endtag(tag)
        if self.in_table:
            if tag == 'table':
                self.in_table = False
                self.final_data.append(self.temp_table)
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

    def handle_data(self, data):
        if self.in_table:
            data = data.replace('\n', '')
            if self.in_key:
                self.temp_key += data
            elif self.in_value:
                self.temp_value += data


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
                elif 'characters' in id_span:
                    self.in_combat = False
                # TODO MIRAR <b>SEE WIKIPEDIA ENTRY:</b>

            elif tag == 'hr':
                while '\n\n\n' in self.temp_combat:
                    self.temp_combat = self.temp_combat.replace('\n\n\n', '\n\n')
                if self.temp_combat:
                    clean_comb = self.temp_combat.replace('\n\n', '')
                    if clean_comb[:6].upper() == 'COMBAT':
                        clean_comb = clean_comb[6:]
                    if clean_comb.startswith('\n'):
                        clean_comb = clean_comb[1:]
                    #Esto lo quita en mayúsculas
                    sin_wiki = clean_comb.partition('SEE WIKIPEDIA ENTRY:')
                    #Esto lo quita en unos pocos que está en Capitalize
                    sin_cap_wiki = sin_wiki[0].partition('See Wikipedia Entry:')
                    #Esto lo quita en el true dragon
                    sin_entries = sin_cap_wiki[0].partition('Wikipedia Entries')
                    self.final_data['Combate'] = sin_entries[0]

    def handle_data(self, data):
        if self.in_combat:
            self.temp_combat += data


class AsCharactersParser(BaseParser):
    def __init__(self, *arg, **kwargs):
        super(AsCharactersParser, self).__init__(*arg, **kwargs)
        self.in_characters = False
        self.in_char_key = False
        self.temp_characters = ''
        self.temp_char_key = ''

    def handle_starttag(self, tag, attrs):
        super(AsCharactersParser, self).handle_starttag(tag, attrs)
        if self.start:
            attrs = dict(attrs)
            id_span = attrs.get('id', '')
            if tag == 'span' and 'CHARACTERS' in id_span.upper():
                self.in_characters = True
                self.in_char_key = True

            elif tag == 'hr':
                while '\n\n\n' in self.temp_characters:
                    self.temp_characters = self.temp_characters.replace('\n\n\n', '\n\n')
                if self.temp_characters:
                    clean_comb = self.temp_characters.replace('\n\n', '')
                    if clean_comb[:6].upper() == 'COMBAT':
                        clean_comb = clean_comb[6:]
                    if clean_comb.startswith('\n'):
                        clean_comb = clean_comb[1:]
                    #Esto lo quita en mayúsculas
                    sin_wiki = clean_comb.partition('SEE WIKIPEDIA ENTRY:')
                    #Esto lo quita en unos pocos que está en Capitalize
                    sin_cap_wiki = sin_wiki[0].partition('See Wikipedia Entry:')
                    #Esto lo quita en el true dragon
                    sin_entries = sin_cap_wiki[0].partition('Wikipedia Entries')
                    self.final_data[self.temp_char_key.capitalize()] = sin_entries[0]

    def handle_endtag(self, tag):
        if tag == 'span':
            self.in_char_key = False

    def handle_data(self, data):
        if self.in_char_key:
            self.temp_char_key += data
        elif self.in_characters:
            self.temp_characters += data


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
        self.parsers = [NameParser, MultiTableParser, DescriptionParser, CombatParser, AsCharactersParser]
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
        name = path[path.rfind(':')+1:]
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
        with open(filename.replace('.html', '.json'), 'w') as f2:
            response = json.dumps(parsers.data, indent=2)
            f2.write(response)
            if to_print:
                print(filename)


class SRD35_JsonClean(object):
    def __init__(self, json_file: str):
        self.json_file: str = json_file
        with open(self.json_file) as f:
            self.initial_data: dict = json.load(f)
        self.final_data: dict = {}

    def excluyendo_ficheros(self, to_print=False) -> bool:
        files_to_exclude = []
        found = False
        if 'Demon' in self.json_file:
            found = True
        if 'Devil' in self.json_file:
            found = True
        if 'Dire_Animal' in self.json_file:
            found = True
        enumerated_data = enumerate(self.initial_data)
        for index, dictionary in enumerated_data:
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
                    if 'Monstruo y Nivel' in key:
                        found = True
                    if 'Size/Type' in key:
                        found = True
            if index != 0:
                pass
        if not found:
            filename = (os.path.realpath(self.json_file))
            excluded_folder = os.path.join(filename, '..', '..', 'EXCLUDED')
            if not os.path.isdir(excluded_folder):  # Si el directorio pasado como argumento no existe:
                os.mkdir(excluded_folder)  # Crea el directorio pasado como argumento
            shutil.copy2(filename, excluded_folder)
            files_to_exclude.append(filename)
            os.remove(filename)
            if to_print:
                print(filename)

    def insertando_titulos(self, to_print=False) -> None:
        name_found = False
        enumerated_data = enumerate(self.initial_data)
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
        filename = (os.path.realpath(self.json_file))
        tipos_folder = os.path.join(filename, '..', 'TIPOS')
        dragon_folder = os.path.join(tipos_folder, 'DRAGONES')
        if not os.path.isdir(dragon_folder):
            os.makedirs(dragon_folder)
        with open(self.json_file, 'r+') as f:
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
                        if 'Size/Type' in key:
                            criatura_tipo = True
                        else:
                            pass
            if not criatura_tipo:
                shutil.copy2(filename, tipos_folder)
                files_to_exclude.append(filename)
                monster = os.path.basename(filename)
                if to_print:
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
                else:
                    for index, elem in enumerated_data:
                        for key, val in elem.items():
                            if 'dragon' in val.lower():
                                is_dragon = True
                    if is_dragon:
                        filename = (os.path.realpath(path))
                        shutil.copy2(filename, dragon_folder)
                        if to_print:
                            print('El archivo ', monster, ' ha sido movido a la carpeta DRAGONES')
                        f.close()
                        os.remove(filename)

    def checking_files(self) -> None:
        pass  # TODO


def checking_files(folder):
    CLAVES = {'Monstruo y Nivel', 'Size/Type', 'Hit Dice', 'Initiative', 'Speed', 'Armor Class',
              'Base Attack/Grapple', 'Attack', 'Full Attack', 'Space/Reach', 'Special Attacks', 'Special Qualities',
              'Saves', 'Abilities', 'Skills', 'Feats', 'Environment', 'Organization', 'Challenge Rating', 'Treasure',
              'Alignment', 'Advancement', 'Level Adjustment'}
    tiene_nombre = False
    vacios = []
    sin_nombre = []
    for path in glob.glob('{}/*.json'.format(folder)):
        with open(path, 'r') as f:
            data = json.load(f)
            enumerated_data = enumerate(data)
            if not data:
                vacios.append(path)
            else:
                for index, elem in enumerated_data:
                    clean_keys = set()
                    if index > 1:
                        pass
                    if index == 0:
                        for key, val in elem.items():
                            if 'Nombre' in key:
                                tiene_nombre = True
                                # print('Nombre de la criatura: ', val)
                            else:
                                sin_nombre.append(path)
                    if index == 1:
                        for key, val in elem.items():
                            if val:
                                clean_keys.add(key)
                        if clean_keys != CLAVES:
                            print(os.path.basename(path) + ': No tiene todas las CLAVES')
                            claves_de_mas = clean_keys.difference(CLAVES)
                            if claves_de_mas:
                                print('Tiene las siguientes CLAVES de más: ')
                            print('Le faltan las siguientes CLAVES: ')
                            print(CLAVES.difference(clean_keys), '\n')
    if vacios:
        print('Los siguientes archivos están vacíos: ')
        for elem in vacios:
            print(elem)
    if sin_nombre:
        print('Las siguientes criaturas no tienen nombre: ')
        for elem in sin_nombre:
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
    jfolder = os.path.join(backup_folder, 'JSON')

    if args.h_folder:
        hfolder = os.path.normpath(args.h_folder)
    if args.j_folder:
        jfolder = os.path.normpath(args.j_folder)

    # dir_path = os.path.dirname(os.getcwd())
    # os.path.normpath(dir_path)
    # backup_folder = os.path.join(dir_path, 'raw')
    # html_folder = os.path.join(backup_folder, 'HTML')
    # json_folder = os.path.join(backup_folder, 'JSON')

    if args.download:
        if not os.path.isdir(hfolder):
            os.makedirs(hfolder)
        if args.quiet:
            dumper_html(hfolder)
        elif args.verbose:
            print('Se están recogiendo los archivos HTML...')
            dumper_html(hfolder, to_print=True)
            print('¡Proceso completado!')
        else:
            print('Se están recogiendo los archivos HTML, por favor espere...')
            dumper_html(hfolder)
            print('¡Proceso completado!')

    if args.to_json:
        if not os.path.isdir(jfolder):
            os.makedirs(jfolder)
        if args.quiet:
            to_json(hfolder, jfolder)
        elif args.verbose:
            print('Creando ficheros JSON...')
            to_json(hfolder, jfolder, to_print=True)
            print('¡Proceso completado!')
        else:
            print('Se están recogiendo los archivos JSON, por favor espere...')
            to_json(hfolder, jfolder)
            print('¡Proceso completado!')

    if args.clean:
            if args.quiet:
                for path in glob.glob('{}/*.json'.format(jfolder)):
                    SRD35_JsonClean(path).excluyendo_ficheros()
                    SRD35_JsonClean(path).insertando_titulos()
                    SRD35_JsonClean(path).organizando_tipos()
            elif args.verbose:
                print('Excluyendo ficheros innecesarios...')
                for path in glob.glob('{}/*.json'.format(jfolder)):
                    SRD35_JsonClean(path).excluyendo_ficheros(to_print=True)
                print('¡Proceso completado!')
                print('Insertando nombre a los siguientes archivos:')
                for path in glob.glob('{}/*.json'.format(jfolder)):
                    SRD35_JsonClean(path).insertando_titulos(to_print=True)
                print('¡Proceso completado!')
                print('Clasificando monstruos...')
                for path in glob.glob('{}/*.json'.format(jfolder)):
                    SRD35_JsonClean(path).organizando_tipos(to_print=True)
                print('¡Proceso completado!')
            else:
                print('Espere mientras se filtran los archivos...')
                for path in glob.glob('{}/*.json'.format(jfolder)):
                    SRD35_JsonClean(path).excluyendo_ficheros()
                    SRD35_JsonClean(path).insertando_titulos()
                    SRD35_JsonClean(path).organizando_tipos()
                print('¡Proceso Completado!')

    if args.checking:
        print('Analizando archivos...')
        checking_files(jfolder)
        print('¡Proceso Completado!')

    # PASO 3 - Excluir los ficheros que no sirven
    # excluyendo_ficheros(json_folder)
    # PASO 4 - Insertando titulos en los ficheros que no tienen
    # insertando_titulos(json_folder)
    # PASO 5 - Pone todos los monstruos que sean un tipo en un directorio y los dragones en una carpeta a parte
    # organizando_tipos(json_folder)

    # checking_files(json_folder)  #TODO PASO 6 - Chequear todos las claves y valores de las tablas

    # multiplecreatures2jsondumper(html_folder)

    # backup_folder = Path('/monstersdb/monstersdb/raw')


if __name__ == '__main__':
    main()
