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
    "name": "SeaDogs SailorPoints",
    "description": "Export SailorPoints files",
    "author": "Wazar",
    "version": (0, 9, 9),
    "blender": (4, 4, 1),
    "location": "File > Export",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Export",
}

correction_export_matrix = axis_conversion(
    from_forward='Y', from_up='Z', to_forward='X', to_up='Y')

point_types = {
    'normal':    0,
    'cannonl':   1,
    'cannonr':   2,
    'cannonf':   3,
    'cannonb':   4,
    'mast1':     5,
    'mast2':     6,
    'mast3':     7,
    'mast4':     8,
    'mast5':     9,
    'nottarget': 10
}

point_types_r = {
    0: 'normal',
    1: 'cannonl',
    2: 'cannonr',
    3: 'cannonf',
    4: 'cannonb',
    5: 'mast1',
    6: 'mast2',
    7: 'mast3',
    8: 'mast4',
    9: 'mast5' ,
    10:'nottarget'
}


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
    def __init__(self, idx, matrix, point_type):
        self.matrix = matrix
        self.point_type = point_type
        self.idx = idx


class SailorPoints:
    def __init__(self):
        self.points = []
        self.links = []
        
    def generate(self, file_path='', report_func=None):
        for i in range(len(self.points)):
            if self.points[i] is None:
                report_func({'ERROR'}, 'point with number "{}" not found'.format(i))
                return {'CANCELLED'}
        for i in range(len(self.links)):
            if self.links[i] is None:
                report_func({'ERROR'}, 'link with number "{}" not found'.format(i))
                return {'CANCELLED'}
        with open(file_path, 'w') as file:
            file.write('[SIZE]\n')
            file.write('points = {}\n'.format(len(self.points)))
            file.write('links = {}\n'.format(len(self.links)))
            file.write('\n')
            file.write('[POINT_DATA]\n')
            for i in range(len(self.points)):
                matrix = correction_export_matrix.to_4x4() @ self.points[i].matrix
                matrix.translation *= Vector([-1, 1, 1])
                vec = matrix.translation
                file.write('point {} = {:.6f},{:.6f},{:.6f},{}\n'.format(i, vec[0], vec[1], vec[2], point_types[self.points[i].point_type]))
                
            file.write('\n')
            file.write('[LINK_DATA]\n')
            for i in range(len(self.links)):
                file.write('link {} = {},{}\n'.format(i, self.links[i].points[0], self.links[i].points[1]))
        return None



def export_sailorpoints(context, file_path="", report_func=None):
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    root = bpy.context.view_layer.objects.active
    root_children = root.children

    collection = root.users_collection[0]


    points = []
    

    # TODO get list of childrens children
    for child in root_children:
        if child.type == 'EMPTY' and child.name == 'points':
            locator = child
            for child in locator.children:
                if child.type == 'EMPTY':
                    points.append(child)
            break

   
    bpy.context.scene.frame_set(0)

    bpy.context.scene.cursor.location = root.location
    bpy.context.view_layer.objects.active = root
    sp = SailorPoints()
    sp.points = [None] * len(points)
    
    for point in points:
        label_name = remove_blender_name_postfix(point.name)
        label_m = Matrix(point.matrix_world)
        
        parts = label_name.split('_')
        if len(parts) != 2:
            report_func({'ERROR'}, 'wrong locator name "{}"; should be <type>_<number>'.format(label_name))
            return {'CANCELLED'} 

        num = int(parts[1])
        if num >= len(points) or num < 0:
            report_func({'ERROR'}, 'the point numbers must be a continuous sequence')
            return {'CANCELLED'} 
    
        if sp.points[num] is not None:
            report_func({'ERROR'}, 'duplicate point number "{}"'.format(num))
            return {'CANCELLED'}
        
        if parts[0] not in point_types:
            report_func({'ERROR'}, 'unknown point type "{}"'.format(parts[0]))
            return {'CANCELLED'}
        sp.points[num] = Point(num, label_m, parts[0])

    
    ret = sp.generate(file_path, report_func)
    if ret is not None:
        return {'CANCELLED'}
        

    print('\nSailorPoints Export finished successfully!')

    return {'FINISHED'}


class ExportSailorPoints(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export.sailorpoints"
    bl_label = "Export sailorpoints"

    # ExportHelper mixin class uses this
    filename_ext = ".ini"

    filter_glob: StringProperty(
        default="*.ini",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return export_sailorpoints(context, self.filepath, report_func=self.report)


def menu_func_export(self, context):
    self.layout.operator(ExportSailorPoints.bl_idname,
                         text="SailorPoints Export(.ini)")


def register():
    bpy.utils.register_class(ExportSailorPoints)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportSailorPoints)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
