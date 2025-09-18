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
    "name": "SeaDogs Foam",
    "description": "Import Foam files",
    "author": "Wazar",
    "version": (1, 0, 0),
    "blender": (4, 4, 1),
    "location": "File > Import",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import",
}



correction_matrix = axis_conversion(
    from_forward='X', from_up='Y', to_forward='Y', to_up='Z')

class Point:
    def __init__(self, idx, matrix, links):
        self.matrix = matrix
        self.idx = idx
        self.links = links


class Foam:
    def __init__(self):
        self.points = {}
        pass
        
    def parse(self, file_path='', report_func=None):
        state = 'init'
        depth_file = None
        v_box_center = None
        v_box_size = None
        with open(file_path, mode='r') as file:
            for line in file:
                line = line.strip()
                if state == 'init':
                    if line.startswith('[Main]'):
                        state = 'main'      
                elif state == 'main':
                    if line.startswith('DepthFile'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        depth_file = parts[1]
                    elif line.startswith('vBoxCenter'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        v_box_center = parts[1]
                    elif line.startswith('vBoxSize'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        v_box_size = parts[1]
                    elif line.startswith('[GraphPoints]'):
                        state = 'points'

                elif state == 'points':
                    if line.startswith('pnt'):
                        line = line.split(sep=';')[0]
                        parts = line.split(sep='=')
                        num = parts[0].strip()[3:]
                        num = int(num)
                        
                        data = parts[1].split(sep=',')
                        coords = [float(v.strip()) for v in data[:2]]
                        
                        matrix = mathutils.Matrix.Translation((coords[0], 0, coords[1]))
                        matrix.translation *= mathutils.Vector([-1, 1, 1])
                        matrix = correction_matrix.to_4x4() @ matrix
                        if data[-1] == '':
                            data.pop()
                        links = [int(v.strip()) for v in data[2:]]

                        self.points[num] = Point(num, matrix, links)
                else:
                    report_func({'ERROR'}, 'Unknown state')
        return None



def parse_sp(file_path="", report_func=None):
    sp = Foam()
    ret = sp.parse(file_path, report_func)
    if ret is not None:
        return {'CANCELLED'};
    return sp

def import_foam(
    context,
    file_path="",
    report_func=None
):
    file_name = os.path.basename(file_path)[:-4]
    data = parse_sp(file_path, report_func)
    
    if data == {'CANCELLED'}:
        return {'CANCELLED'}

    collection = bpy.data.collections.new(file_name)
    bpy.context.scene.collection.children.link(collection)

    root = bpy.data.objects.new("root", None)
    root['ExportType'] = 'FoamIsland'
    collection.objects.link(root)

    blender_objects = []
    points_locator_name = 'points'  
    points_locator = bpy.data.objects.new(points_locator_name, None)
    collection.objects.link(points_locator)
    points_locator.parent = root

    
    for idx in data.points:

        locator_name = 'pnt{:04d}'.format(data.points[idx].idx)
        
        locator = bpy.data.objects.new(locator_name, None)
        collection.objects.link(locator)
        locator.parent = points_locator
        locator.empty_display_type = 'ARROWS'
        locator.empty_display_size = 0.5
        locator.matrix_basis = data.points[idx].matrix
        data.points[idx].locator = locator



    for idx in data.points:
        for i in range(len(data.points[idx].links) - 1):
            first_point = data.points[data.points[idx].links[i]]
            second_point = data.points[data.points[idx].links[i+1]]
            if first_point.idx == second_point.idx:
                continue
            constraint = first_point.locator.constraints.new(type='TRACK_TO')
            constraint.target = second_point.locator
            constraint.name = 'pnt{:04d}_{}'.format(idx, i)
            #print('pnt{}_{}| first_point: "{}" second_point: "{}"'.format(idx, i, first_point.locator.name, second_point.locator.name))

        
    return {'FINISHED'}

class ImportFoam(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import.foam"
    bl_label = "Import foam"

    # ImportHelper mixin class uses this
    filename_ext = ".ini"

    filter_glob: StringProperty(
        default="*.ini",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

   

    def execute(self, context):
        return import_foam(context, self.filepath, report_func=self.report)


def menu_func_import_foam(self, context):
    self.layout.operator(ImportFoam.bl_idname,
                         text="Foam Import(.ini)")


def register():
    bpy.utils.register_class(ImportFoam)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_foam)


def unregister():
    bpy.utils.unregister_class(ImportFoam)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_foam)


if __name__ == "__main__":
    register()
