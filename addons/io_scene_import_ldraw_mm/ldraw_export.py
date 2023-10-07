import bpy
import bmesh
import math

from .ldraw_file import LDrawFile
from .ldraw_node import LDrawNode
from .ldraw_color import LDrawColor
from .filesystem import FileSystem
from .export_options import ExportOptions
from . import strings
from . import helpers
from . import ldraw_props
from . import matrices


# edges marked sharp will be output as line type 2
# tris => line type 3
# quads => line type 4
# conditional lines => line type 5 and ngons, aren't handled
# header file is determined by ldraw_props of active object
# if obj.ldraw_props.export_polygons current object being iterated will be exported as line type 2,3,4
# otherwise line type 1
def do_export(filepath):
    LDrawFile.reset_caches()
    LDrawNode.reset_caches()
    FileSystem.build_search_paths(parent_filepath=filepath)
    LDrawFile.read_color_table()

    active_object = bpy.context.object
    all_objects = bpy.context.scene.objects
    selected_objects = bpy.context.selected_objects
    active_objects = bpy.context.view_layer.objects.active

    objects = all_objects
    if ExportOptions.selection_only:
        objects = selected_objects

    if active_object is None:
        print("No selected objects")
        return

    name = active_object.ldraw_props.name

    # no filename specified on object
    if name == "" or name is None:
        print(f"Active object {active_object.name} does not have a name")
        return False

    ldraw_file = LDrawFile("")
    ldraw_file.filename = active_object.ldraw_props.filename
    ldraw_file.description = active_object.ldraw_props.description
    ldraw_file.name = active_object.ldraw_props.name
    ldraw_file.author = active_object.ldraw_props.author
    ldraw_file.part_type = active_object.ldraw_props.part_type
    ldraw_file.actual_part_type = active_object.ldraw_props.actual_part_type
    ldraw_file.optional_qualifier = active_object.ldraw_props.optional_qualifier
    ldraw_file.update_date = active_object.ldraw_props.update_date
    ldraw_file.license = active_object.ldraw_props.license
    # ldraw_file.category = active_object.ldraw_props.category
    # ldraw_file.keywords = active_object.ldraw_props.keywords
    # ldraw_file.history = active_object.ldraw_props.history

    is_like_model = ldraw_file.is_model() or ldraw_file.is_shortcut()
    hlines = ldraw_props.get_header_lines(active_object, is_like_model)
    for hline in hlines:
        ldraw_file.lines.append(hline)

    subfile_obj_names = []
    polygon_obj_names = []

    for obj in objects:
        # so objects that are not linked to the scene don't get exported
        # objects during a failed export would be such an object
        if obj.users < 1:
            continue

        if obj.ldraw_props.export_polygons:
            polygon_obj_names.append(obj.name)
        else:
            subfile_obj_names.append(obj.name)

    if len(subfile_obj_names) > 0:
        ldraw_file.lines.append("\n")
    for name in subfile_obj_names:
        obj = bpy.data.objects.get(name)
        aa = get_matrix(obj)
        __export_subfiles(obj, aa, ldraw_file.lines)

    if len(polygon_obj_names) > 0:
        ldraw_file.lines.append("\n")
    part_lines = []
    for name in polygon_obj_names:
        obj = bpy.data.objects.get(name)
        aa = get_matrix(obj)
        __export_polygons(obj, aa, part_lines)

    sorted_part_lines = sorted(part_lines, key=lambda pl: (int(pl[1]), int(pl[0])))

    current_color_code = None
    joined_part_lines = []
    for line in sorted_part_lines:
        if len(line) > 2:
            new_color_code = line[1]
            if new_color_code != current_color_code:
                if current_color_code is not None:
                    joined_part_lines.append("\n")

                current_color_code = new_color_code
                color = LDrawColor.get_color(current_color_code)

                joined_part_lines.append(f"0 // {color.name}")

        joined_part_lines.append(" ".join(line))
    ldraw_file.lines.extend(joined_part_lines)

    with open(filepath, 'w', encoding='utf-8', newline="\n") as file:
        for line in ldraw_file.lines:
            file.write(line)
            if line != "\n":
                file.write("\n")

    for obj in selected_objects:
        if not obj.select_get():
            obj.select_set(True)

    bpy.context.view_layer.objects.active = active_objects


# if object wasn't imported, export it directly
# if object was imported, invert import matrices
# inverting parent matrix doesn't work for some reason
# parent.matrix_world is already applied to obj.matrix_world
def get_matrix(obj):
    parent_invert_import_scale_matrix = obj.parent and obj.parent.ldraw_props.invert_import_scale_matrix
    object_invert_import_scale_matrix = obj.ldraw_props.invert_import_scale_matrix
    invert_import_scale_matrix = parent_invert_import_scale_matrix or object_invert_import_scale_matrix

    invert_gap_scale_matrix = obj.ldraw_props.invert_gap_scale_matrix

    if invert_import_scale_matrix and invert_gap_scale_matrix:
        aa = matrices.import_scale_matrix.inverted() @ obj.matrix_world @ matrices.gap_scale_matrix.inverted()
    elif invert_import_scale_matrix:
        aa = matrices.import_scale_matrix.inverted() @ obj.matrix_world
    elif invert_gap_scale_matrix:
        aa = obj.matrix_world @ matrices.gap_scale_matrix.inverted()
    else:
        aa = obj.matrix_world

    return matrices.rotation_matrix.inverted() @ aa


# https://devtalk.blender.org/t/to-mesh-and-creating-new-object-issues/8557/4
# https://docs.blender.org/api/current/bpy.types.Depsgraph.html
def __clean_mesh(obj):
    bm = bmesh.new()
    bm.from_object(obj, bpy.context.evaluated_depsgraph_get())

    faces = None
    if ExportOptions.triangulate:
        faces = bm.faces
    elif ExportOptions.ngon_handling == "triangulate":
        faces = []
        for f in bm.faces:
            if len(f.verts) > 4:
                faces.append(f)
    if faces is not None:
        bmesh.ops.triangulate(bm, faces=faces, quad_method='BEAUTY', ngon_method='BEAUTY')

    if ExportOptions.remove_doubles:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=ExportOptions.merge_distance)

    if ExportOptions.recalculate_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = obj.data.copy()
    helpers.finish_bmesh(bm, mesh)
    return mesh


# https://stackoverflow.com/a/2440786
# https://www.ldraw.org/article/512.html#precision
def __fix_round(number, places=None):
    if type(places) is not int:
        places = 2
    x = round(number, places)
    value = ("%f" % x).rstrip("0").rstrip(".")

    # remove -0
    if value == "-0":
        value = "0"

    return value


# TODO: if obj["section_label"] then:
#  0 // f{obj["section_label"]}
def __export_subfiles(obj, aa, lines):
    filename = obj.ldraw_props.filename
    if filename == "" or filename is None:
        print(f"Object {obj.name} does not have a filename")
        return

    color_code = obj.ldraw_props.color_code
    if color_code == "" or color_code is None:
        print(f"Object {obj.name} does not have a color_code")
        return

    color = LDrawColor.get_color(color_code)
    color_code = color.code

    precision = obj.ldraw_props.export_precision

    a = __fix_round(aa[0][0], precision)
    b = __fix_round(aa[0][1], precision)
    c = __fix_round(aa[0][2], precision)
    x = __fix_round(aa[0][3], precision)

    d = __fix_round(aa[1][0], precision)
    e = __fix_round(aa[1][1], precision)
    f = __fix_round(aa[1][2], precision)
    y = __fix_round(aa[1][3], precision)

    g = __fix_round(aa[2][0], precision)
    h = __fix_round(aa[2][1], precision)
    i = __fix_round(aa[2][2], precision)
    z = __fix_round(aa[2][3], precision)

    line = f"1 {color_code} {x} {y} {z} {a} {b} {c} {d} {e} {f} {g} {h} {i} {filename}"

    lines.append(line)


def __export_polygons(obj, aa, lines):
    # obj is an empty
    if obj.data is None:
        return False

    if obj.type != 'MESH':
        return False

    mesh = __clean_mesh(obj)

    precision = obj.ldraw_props.export_precision

    # export faces
    face_edge_maps = {}
    for polygon in mesh.polygons:
        # build list of edges and their shared faces
        for ff in mesh.polygons:
            if polygon.index == ff.index:
                continue
            for fek in polygon.edge_keys:
                ek = edge_key(fek[0], fek[1])
                face_edge_maps.setdefault(ek, set()).add(polygon.index)

        length = len(polygon.vertices)
        line_type = None
        if length == 3:
            line_type = "3"
        elif length == 4:
            line_type = "4"
        if line_type is None:
            continue

        obj_color_code = obj.ldraw_props.color_code
        if obj_color_code == "" or obj_color_code is None:
            print(f"Object {obj.name} does not have a color_code")
            return
        obj_color = LDrawColor.get_color(obj_color_code)

        color_code = "16"
        color = LDrawColor.get_color(color_code)

        if polygon.material_index + 1 <= len(mesh.materials):
            material = mesh.materials[polygon.material_index]
            if strings.ldraw_color_code_key in material:
                color_code = str(material[strings.ldraw_color_code_key])
                color = LDrawColor.get_color(color_code)

        if color.code != "16":
            color_code = color.code
        else:
            color_code = obj_color.code

        line = [line_type, color_code]
        for v in polygon.vertices:
            co = aa @ mesh.vertices[v].co
            for vv in co:
                line.append(__fix_round(vv, precision))

        lines.append(line)

    af = 1.0
    ac = 60
    ae = 90
    flat = []
    shallow = []
    sharp = []

    for edge_keys, faces in face_edge_maps.items():
        f_list = list(faces)
        if len(f_list) < 2:
            continue

        n1 = mesh.polygons[f_list[0]].normal
        n2 = mesh.polygons[f_list[1]].normal

        dot = n1.dot(n2)
        # domain error workaround for when dot <-1 or >1
        if dot > 1:
            dot = 1
        elif dot < -1:
            dot = -1

        rad_angle = abs(math.acos(dot))
        deg_angle = math.degrees(rad_angle)

        if deg_angle < af:  # angle is flat, no condline
            flat.append(edge_keys)
        elif deg_angle < ac:  # angle is shallow, condline
            shallow.append(edge_keys)
        else:  # elif deg_angle < ae: # angle is steep. make sharp edge, for best results, manually mark desired sharp edges as sharp, also add edges where model sections interect
            sharp.append(edge_keys)

    for e in mesh.edges:
        ek = edge_key(e.vertices[0], e.vertices[1])

        if ek in sharp or e.use_edge_sharp:
            line = ["2", "24"]
            for v in e.vertices:
                co = aa @ mesh.vertices[v].co
                for vv in co:
                    line.append(__fix_round(vv, precision))
            lines.append(line)
        # elif ek in shallow: # for best results, if edge isn't sharp, it's a condline
        else:
            if not obj.ldraw_props.export_shade_smooth:
                continue

            if ek not in face_edge_maps:
                continue

            faces = list(face_edge_maps[ek])

            # don't use edges that have less than 2 faces
            if len(faces) < 2:
                continue

            line = ["5", "24"]
            for v in e.vertices:
                co = aa @ mesh.vertices[v].co
                for vv in co:
                    line.append(__fix_round(vv, precision))

            f1 = faces[0]
            f2 = faces[1]

            face1 = mesh.polygons[f1]
            face2 = mesh.polygons[f2]

            # choose edges that are connected to the condline that aren't the condline
            edge_keys1 = [x for x in face1.edge_keys if edge_key(x[0], x[1]) != ek]
            edge_keys2 = [x for x in face2.edge_keys if edge_key(x[0], x[1]) != ek]

            # use the points that aren't the pin as the control points
            pin = ek[0]
            control_points = []
            for _edge_keys in [edge_keys1, edge_keys2]:
                for yy in _edge_keys:
                    if pin in yy:
                        control_point = [x for x in yy if x != pin][0]
                        control_points.append(control_point)

            for v in control_points:
                co = aa @ mesh.vertices[v].co
                for vv in co:
                    line.append(__fix_round(vv, precision))

            lines.append(line)

    bpy.data.meshes.remove(mesh)

    return True


def edge_key(i1, i2):
    return (min(i1, i2), max(i1, i2))
