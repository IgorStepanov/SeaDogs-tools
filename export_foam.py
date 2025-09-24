from math import sqrt, ceil
import struct
import time
import re
import sys
import cProfile

import bmesh
import bpy
from mathutils import Vector, Matrix
from collections import defaultdict
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, axis_conversion

sys.setrecursionlimit(10000)

    
bl_info = {
    "name": "SeaDogs island foam export",
    "description": "Export Foam files",
    "author": "Wazar",
    "version": (1, 1, 1),
    "blender": (4, 4, 1),
    "location": "File > Export",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Export",
}

correction_export_matrix = axis_conversion(
    from_forward='Y', from_up='Z', to_forward='X', to_up='Y')


def remove_blender_name_postfix(name):
    return re.sub(r'\.\d{3}', '', name)
    
def convert_coordinate_from_ini(coord):
    return (coord[2], -coord[0], coord[1])


def convert_coordinate_to_ini(coord):
    return (-coord[1], coord[2], coord[0])


class Link:
    def __init__(self, idx, points):
        self.points = points
        self.idx = idx

class Point:
    def __init__(self, idx, matrix, links):
        self.matrix = matrix
        self.idx = idx
        self.links = links


class Foam:
    def __init__(self, depth_file, v_box_center, v_box_size):
        self.points = []
        self.depth_file = depth_file
        self.v_box_center = v_box_center
        self.v_box_size = v_box_size
        
    def generate(self, file_path='', report_func=None):
        with open(file_path, 'w') as file:
            file.write('[Main]\n')
            file.write('DepthFile = {}\n'.format(self.depth_file))
            file.write('vBoxCenter = {}\n'.format(self.v_box_center))
            file.write('vBoxSize = {}\n'.format(self.v_box_size))
            file.write('\n')
            file.write('[GraphPoints]\n')
            for i in range(len(self.points)):
                matrix = correction_export_matrix.to_4x4() @ self.points[i].matrix
                matrix.translation *= Vector([-1, 1, 1])
                vec = matrix.translation
                links = [str(v[0])+","+str(v[1]) for v in self.points[i].links]

                file.write('pnt{} = {:.0f},{:.0f},{},{},\n'.format(self.points[i].idx, vec[0], vec[2], len(links), ','.join(links)))
                
            file.write('\n')
        return None



def export_foam(context, file_path="", report_func=None):
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    root = bpy.context.view_layer.objects.active
    root_children = root.children

    collection = root.users_collection[0]


    points = []
    depth_file = None
    v_box_center = None
    v_box_size = None

    # TODO get list of childrens children
    for child in root_children:
        if child.type == 'EMPTY' and child.name == 'points':
            locator = child
            depth_file = locator['DepthFile']
            if depth_file is None:
                depth_file = ''
            v_box_center = locator['vBoxCenter']
            if v_box_center is None:
                v_box_center = ''
            v_box_size = locator['vBoxSize']
            if v_box_size is None:
                v_box_size = ''
            for child in locator.children:
                if child.type == 'EMPTY':
                    points.append(child)
            break

    points.sort(key=lambda point : remove_blender_name_postfix(point.name))
    bpy.context.scene.frame_set(0)

    bpy.context.scene.cursor.location = root.location
    bpy.context.view_layer.objects.active = root
    sp = Foam(depth_file, v_box_center, v_box_size)
    sp.points = [None] * len(points)
    
    loc_to_point = {}
    num = 0
    for point in points:
        label_name = remove_blender_name_postfix(point.name)
        label_m = Matrix(point.matrix_world)

        sp.points[num] = Point(num, label_m, [])
        
        loc_to_point[label_name] = sp.points[num]
        num += 1

    links = []
    links_to_point_loc = {}
    num = 0

    for point in points:
        for con in point.constraints[:]:
            if con.type != "TRACK_TO":
                continue
            links_to_point_loc[con.name] = point
            links.append(con)


    links.sort(key=lambda con : remove_blender_name_postfix(con.name))


    for con in links:
        link_name = remove_blender_name_postfix(con.name) 

        parts = link_name.split('_')
        base_point_name = parts[0]
        base_point = loc_to_point[base_point_name]
        point = links_to_point_loc[con.name]
        target = con.target
        if target is None:
            report_func({'ERROR'}, 'wrong link "{}"'.format(con.name))
            return {'CANCELLED'}

        if remove_blender_name_postfix(point.name) not in loc_to_point:
            report_func({'ERROR'}, 'wrong point "{}"'.format(point.name))
            return {'CANCELLED'}
            
        if remove_blender_name_postfix(target.name) not in loc_to_point:
            report_func({'ERROR'}, 'wrong point "{}"'.format(target.name))
            return {'CANCELLED'}

        src_idx = loc_to_point[remove_blender_name_postfix(point.name)].idx
        dst_idx = loc_to_point[remove_blender_name_postfix(target.name)].idx

        base_point.links.append((src_idx, dst_idx))


    ret = sp.generate(file_path, report_func)
    if ret is not None:
        return {'CANCELLED'}
        

    print('\nFoam Export finished successfully!')

    return {'FINISHED'}


class ExportFoam(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export.foam"
    bl_label = "Island foam export"

    # ExportHelper mixin class uses this
    filename_ext = ".ini"

    filter_glob: StringProperty(
        default="*.ini",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    def invoke(self, context, event):
        selected_object = context.view_layer.objects.active
        if selected_object:
            collection = selected_object.users_collection[0]
            self.filepath = remove_blender_name_postfix(collection.name) + self.filename_ext
            
        return super().invoke(context, event)

    def execute(self, context):
        return export_foam(context, self.filepath, report_func=self.report)


def menu_func_export(self, context):
    self.layout.operator(ExportFoam.bl_idname,
                         text="Island foam export (.ini)")


def register():
    bpy.utils.register_class(ExportFoam)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportFoam)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
