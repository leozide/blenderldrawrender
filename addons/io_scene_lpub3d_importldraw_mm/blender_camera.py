import math
import bpy

from .import_options import ImportOptions
from . import blender_lookat
from . import group


def create_camera(camera, empty=None, collection=None):
    blender_camera = bpy.data.cameras.new(camera.name)

    blender_camera.sensor_fit = "VERTICAL"
    # camera.sensor_height = self.fov
    blender_camera.lens_unit = "FOV"
    blender_camera.angle = math.radians(camera.fov)  # self.fov * 3.1415926 / 180.0
    blender_camera.clip_start = camera.z_near
    blender_camera.clip_end = camera.z_far

    blender_camera.clip_start = blender_camera.clip_start * ImportOptions.import_scale
    blender_camera.clip_end = blender_camera.clip_end * ImportOptions.import_scale

    camera.position[0] = camera.position[0] * ImportOptions.import_scale
    camera.position[1] = camera.position[1] * ImportOptions.import_scale
    camera.position[2] = camera.position[2] * ImportOptions.import_scale

    camera.target_position[0] = camera.target_position[0] * ImportOptions.import_scale
    camera.target_position[1] = camera.target_position[1] * ImportOptions.import_scale
    camera.target_position[2] = camera.target_position[2] * ImportOptions.import_scale

    camera.up_vector[0] = camera.up_vector[0] * ImportOptions.import_scale
    camera.up_vector[1] = camera.up_vector[1] * ImportOptions.import_scale
    camera.up_vector[2] = camera.up_vector[2] * ImportOptions.import_scale

    if camera.orthographic:
        distance = camera.position - camera.target_position
        dist_target_to_camera = distance.length
        blender_camera.ortho_scale = dist_target_to_camera / 1.92
        blender_camera.type = "ORTHO"
    else:
        blender_camera.type = "PERSP"

    obj = bpy.data.objects.new(camera.name, blender_camera)
    obj.name = camera.name
    obj.location = camera.position
    obj.hide_viewport = camera.hidden
    obj.hide_render = camera.hidden

    if collection is None:
        collection = bpy.context.scene.collection
    group.link_obj(collection, obj)

    # https://blender.stackexchange.com/a/72899
    # https://blender.stackexchange.com/a/154926
    # https://blender.stackexchange.com/a/29148
    # https://docs.blender.org/api/current/info_gotcha.html#stale-data
    # https://blenderartists.org/t/how-to-avoid-bpy-context-scene-update/579222/6
    # https://blenderartists.org/t/where-do-matrix-changes-get-stored-before-view-layer-update/1182838
    # when parenting the location of the parented obj is affected by the transform of the empty
    # this undoes the transform of the empty
    obj.parent = empty
    bpy.context.view_layer.update()
    if obj.parent is not None:
        obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()

    blender_lookat.look_at(obj, camera.target_position, camera.up_vector)

    return obj
