import math
import os
import struct
import time

import bmesh
import bpy
import mathutils
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, axis_conversion

bl_info = {
    "name": "SeaDogs SailorPoints",
    "description": "Import SailorPoints files",
    "author": "Wazar",
    "version": (0, 0, 1),
    "blender": (4, 4, 1),
    "location": "File > Import",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import",
}



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



correction_matrix = axis_conversion(
    from_forward='X', from_up='Y', to_forward='Y', to_up='Z')


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
        pass
        
    def parse(self, file_path='', report_func=None):
        state = 'init'
        points_count = None
        links_count = None
        with open(file_path, mode='r') as file:
            for line in file:
                line = line.strip()
                if state == 'init':
                    if line.startswith('[SIZE]'):
                        state = 'size'
                elif state == 'size':
                    if line.startswith('points'):
                        parts = line.split(sep='=')
                        parts[1] = parts[1].split(sep=';')[0].strip()
                        points_count = int(parts[1])
                    elif line.startswith('links'):
                        parts = line.split(sep='=')
                        parts[1] = parts[1].split(sep=';')[0].strip()
                        links_count = int(parts[1])
                    elif line.startswith('[POINT_DATA]'):
                        state = 'points'
                    elif line.startswith('[LINK_DATA]'):
                        state = 'links'

                    if state == 'links' or state == 'points':
                        if points_count is None:
                            report_func({'ERROR'}, 'point count is not specified')
                            return {'CANCELLED'} 
                        if links_count is None:
                            report_func({'ERROR'}, 'links count is not specified')
                            return {'CANCELLED'} 
                        self.points = [None] * points_count
                        self.links = [None] * links_count
                        
                elif state == 'points':
                    if line.startswith('[LINK_DATA]'):
                        state = 'links'
                    elif line.startswith('point'):
                        line = line.split(sep=';')[0]
                        parts = line.split(sep='=')
                        num = parts[0].split(sep=' ')[1].strip()
                        num = int(num)
                        if num >= points_count or num < 0:
                            report_func({'ERROR'}, 'point number "{}" out of range; max = "{}"'.format(num, points_count - 1))
                            return {'CANCELLED'} 
                        data = parts[1].split(sep=',')
                        coords = [float(v.strip()) for v in data[:3]]
                        
                        matrix = mathutils.Matrix.Translation((coords[0], coords[1], coords[2]))
                        matrix.translation *= mathutils.Vector([-1, 1, 1])
                        matrix = correction_matrix.to_4x4() @ matrix
                        

                        point_type_int = int(data[3].strip())
                        if point_type_int not in point_types_r:
                            report_func({'ERROR'}, 'point type "{}" is unknown'.format(point_type_int))
                            return {'CANCELLED'}
                        point_type = point_types_r[point_type_int]
                        self.points[num] = Point(num, matrix, point_type)
                        
                elif state == 'links':
                    if line.startswith('[POINT_DATA]'):
                        state = 'points'
                    elif line.startswith('link'):
                        line = line.split(sep=';')[0]
                        parts = line.split(sep='=')
                        num = parts[0].split(sep=' ')[1].strip()
                        num = int(num)
                        if num >= links_count or num < 0:
                            report_func({'ERROR'}, 'link number "{}" out of range; max = "{}"'.format(num, links_count - 1))
                            return {'CANCELLED'} 
                        data = parts[1].split(sep=',')
                        points = [int(v.strip()) for v in data[:2]]
                        
                        if points[0] >= points_count or num < 0: 
                            report_func({'ERROR'}, 'point number "{}" out of range; max = "{}"'.format(points[0], points_count - 1))
                            return {'CANCELLED'}
                        if points[1] >= points_count or num < 0: 
                            report_func({'ERROR'}, 'point number "{}" out of range; max = "{}"'.format(points[1], points_count - 1))
                            return {'CANCELLED'} 
                        self.links[num] = Link(num, points)
                            
                else:
                    report_func({'ERROR'}, 'Unknown state')
                    
        for i in range(points_count):
            if self.points[i] is None:
                report_func({'ERROR'}, 'point with number "{}" not found'.format(i))
                return {'CANCELLED'}
                    
        for i in range(links_count):
            if self.links[i] is None:
                report_func({'ERROR'}, 'link with number "{}" not found'.format(i))
                return {'CANCELLED'}
        return None



def parse_sp(file_path="", report_func=None):
    sp = SailorPoints()
    ret = sp.parse(file_path, report_func)
    if ret is not None:
        return {'CANCELLED'};
    return sp

def import_sailorpoints(
    context,
    file_path="",
    report_func=None
):
    file_name = os.path.basename(file_path)[:-4]
    data = parse_sp(file_path, report_func)
    
    if data == {'CANCELLED'}:
        return {'CANCELLED'}

    collection = bpy.data.collections.new(file_name+'_SP')
    bpy.context.scene.collection.children.link(collection)

    root = bpy.data.objects.new("root", None)
    collection.objects.link(root)

    blender_objects = []
    points_locator_name = 'points'  
    points_locator = bpy.data.objects.new(points_locator_name, None)
    collection.objects.link(points_locator)
    points_locator.parent = root

    
    for point in data.points:
        locator_name = '{}_{}'.format(point.point_type, point.idx)
        
        locator = bpy.data.objects.new(locator_name, None)
        collection.objects.link(locator)
        locator.parent = points_locator
        locator.empty_display_type = 'ARROWS'
        locator.empty_display_size = 0.5
        locator.matrix_basis = point.matrix
        point.locator = locator
        
    for link in data.links:
        first_point = data.points[link.points[0]]
        second_point = data.points[link.points[1]]
        
        constraint = first_point.locator.constraints.new(type='TRACK_TO')
        constraint.target = second_point.locator
        constraint.name = 'link_{}'.format(link.idx)
        pass
        
    return {'FINISHED'}

class ImportSailorPoints(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import.sailorpoints"
    bl_label = "Import sailorpoints"

    # ImportHelper mixin class uses this
    filename_ext = ".ini"

    filter_glob: StringProperty(
        default="*.ini",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

   

    def execute(self, context):
        return import_sailorpoints(context, self.filepath, report_func=self.report)


def menu_func_import(self, context):
    self.layout.operator(ImportSailorPoints.bl_idname,
                         text="SailorPoints Import(.ini)")


def register():
    bpy.utils.register_class(ImportSailorPoints)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSailorPoints)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
