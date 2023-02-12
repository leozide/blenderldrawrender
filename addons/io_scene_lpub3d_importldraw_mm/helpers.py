import csv
import io
import re
import codecs
import json
from pathlib import Path
import os

import functools

try:
    from .definitions import APP_ROOT
except ImportError as e:
    from definitions import APP_ROOT


# remove multiple spaces
def clean_line(line):
    return " ".join(line.split())


# assumes cleaned line being passed
def get_params(clean_line, command, lowercase=False):
    no_command = clean_line[len(command):]
    no_command_parts = no_command.split()
    if lowercase:
        return [x.lower() for x in no_command_parts]
    return no_command_parts


def parse_csv_line(line, min_params=0):
    try:
        parts = list(csv.reader(io.StringIO(line), delimiter=' ', quotechar='"', skipinitialspace=True))
    except csv.Error as e:
        parts = [re.split(r"\s+", line)]

    if len(parts) == 0:
        return None

    _params = parts[0]

    if len(_params) == 0:
        return None

    while len(_params) < min_params:
        _params.append("")
    return _params


def fix_string_encoding(string):
    new_string = string
    if type(string) is str:
        new_string = bytes(string.encode())
    for codec in [codecs.BOM_UTF8, codecs.BOM_UTF16, codecs.BOM_UTF32]:
        new_string = new_string.replace(codec, b'')
    new_string = new_string.decode()
    return new_string


def write_json(folder, filename, dictionary):
    try:
        folder = os.path.join(APP_ROOT, folder)
        Path(folder).mkdir(parents=True, exist_ok=True)
        filepath = os.path.join(folder, filename)
        with open(filepath, 'w', encoding='utf-8', newline="\n") as file:
            file.write(json.dumps(dictionary))
    except Exception as e:
        print(e)


def read_json(folder, filename, default=None):
    try:
        folder = os.path.join(APP_ROOT, folder)
        filepath = os.path.join(folder, filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(e)
        return default


def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)


def ensure_bmesh(bm):
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()


def finish_bmesh(bm, mesh):
    bm.to_mesh(mesh)
    bm.clear()
    bm.free()


def finish_mesh(mesh):
    mesh.validate()
    mesh.update(calc_edges=True)


def hide_obj(obj):
    obj.hide_viewport = True
    obj.hide_render = True


def show_obj(obj):
    obj.hide_viewport = False
    obj.hide_render = False
