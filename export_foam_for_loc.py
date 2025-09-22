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
    "name": "SeaDogs location foam export",
    "description": "Export Foam files",
    "author": "Wazar",
    "version": (1, 1, 0),
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


class Point:
    def __init__(self, idx, matrix_1, matrix_2):
        self.idx = idx
        self.matrix_1 = matrix_1
        self.matrix_2 = matrix_2

class FoamElem:
    def __init__(self, points, locator):
        self.points        = points
        self.locator       = locator



class Foam:
    def __init__(self, elems, locator):
        self.locator       = locator
        self.elems = elems
        
    def generate(self, file_path='', report_func=None):
        with open(file_path, 'w') as file:
            file.write('NumFoams = {}\n'.format(len(self.elems)))
            file.write('MaxFoamDistance = {}\n'.format(self.locator['MaxFoamDistance']))
            file.write('FoamDeltaY = {}\n'.format(self.locator['FoamDeltaY']))
            file.write('FoamDivides = {}\n'.format(self.locator['FoamDivides']))
            file.write('\n')
            
            for i in range(len(self.elems)):
                elem = self.elems[i]
                file.write('[foam_{}]\n'.format(i))
                file.write('NumParts = {}\n'.format(len(elem.points)))
                
                file.write('Alpha = {}\n'.format(elem.locator['Alpha']))
                file.write('Speed = {}\n'.format(elem.locator['Speed']))
                file.write('Braking = {}\n'.format(elem.locator['Braking']))
                file.write('Appear = {}\n'.format(elem.locator['Appear']))
                file.write('TexScaleX = {:.3f}\n'.format(elem.locator['TexScaleX']))
                file.write('NumFoams = {}\n'.format(elem.locator['NumFoams']))
                file.write('Texture = {}\n'.format(elem.locator['Texture']))
                file.write('Type = {}\n'.format(elem.locator['Type']))
                for j in range(len(elem.points)):
                    matrix_1 = correction_export_matrix.to_4x4() @ elem.points[j].matrix_1
                    matrix_1.translation *= Vector([-1, 1, 1])
                    vec_1 = matrix_1.translation
                    
                    matrix_2 = correction_export_matrix.to_4x4() @ elem.points[j].matrix_2
                    matrix_2.translation *= Vector([-1, 1, 1])
                    vec_2 = matrix_2.translation
                    file.write('key_{} = {:.4f}, {:.4f}, {:.4f}, {:.4f}\n'.format(j, vec_1[0], vec_1[2], vec_2[0], vec_2[2]))
                file.write('\n')

        return None



def export_foam(context, file_path="", report_func=None):
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    root = bpy.context.view_layer.objects.active
    root_children = root.children

    collection = root.users_collection[0]


    foam_elem_locators = []
    foam_elems = []
    foams_locator = None
    # TODO get list of childrens children
    for child in root_children:
        if child.type == 'EMPTY' and remove_blender_name_postfix(child.name) == 'foams':
            foams_locator = child
            for child in foams_locator.children:
                if child.type == 'EMPTY':
                    foam_elem_locators.append(child)
            break

    foam_elem_locators.sort(key=lambda loc : remove_blender_name_postfix(loc.name))
    
    
    for foam in foam_elem_locators:
        point_locators = []
        points = []
        for child in foam.children:
            if child.type == 'EMPTY':
                point_locators.append(child)
                
        point_locators.sort(key=lambda loc : remove_blender_name_postfix(loc.name))
        if len(point_locators) % 2 == 1:
            report_func({'ERROR'}, 'point count should be even for locator "{}"'.format(foam.name))
            return {'CANCELLED'}
            
        key_count = len(point_locators) // 2
        for j in range(key_count):
            matrix_1 = Matrix(point_locators[j].matrix_world)
            matrix_2 = Matrix(point_locators[j + key_count].matrix_world)
            points.append(Point(j, matrix_1, matrix_2))
            
        foam_elems.append(FoamElem(points, foam))
        

    sp = Foam(foam_elems, foams_locator)


    ret = sp.generate(file_path, report_func)
    if ret is not None:
        return {'CANCELLED'}
        

    print('\nFoam Export finished successfully!')

    return {'FINISHED'}


class ExportFoamForLoc(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export.foam_for_loc"
    bl_label = "Location foam export"

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
    self.layout.operator(ExportFoamForLoc.bl_idname,
                         text="Location foam export (.ini)")


def register():
    bpy.utils.register_class(ExportFoamForLoc)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportFoamForLoc)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
