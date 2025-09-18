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
    "description": "Import Foam for locations files",
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
    def __init__(self, idx, matrix_1, matrix_2):
        self.idx = idx
        self.matrix_1 = matrix_1
        self.matrix_2 = matrix_2

class FoamElem:
    def set(self, num_parts, alpha, speed, braking, appear, tex_scale_x, num_foams, texture, type_, points):
        self.num_parts     = num_parts  
        self.alpha         = alpha      
        self.speed         = speed      
        self.braking       = braking    
        self.appear        = appear     
        self.tex_scale_x   = tex_scale_x
        self.num_foams     = num_foams  
        self.texture       = texture    
        self.type_         = type_      
        self.points        = points

class Foam:
    def __init__(self):
        self.points = {}
        pass
        
    def parse(self, file_path='', report_func=None):
        state = 'init'
        
        cur_foam = None
        
        
        cur_num_parts     = None
        cur_alpha         = None
        cur_speed         = None
        cur_braking       = None
        cur_appear        = None
        cur_tex_scale_x   = None
        cur_num_foams     = None
        cur_texture       = None
        cur_type_         = None
        cur_points        = None
        
        
        with open(file_path, mode='r') as file:
            for line in file:
                line = line.strip()
                if state == 'init':
                    if line.startswith('NumFoams'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        self.num_foams = int(parts[1])
                    elif line.startswith('MaxFoamDistance'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        self.max_foam_distance = int(parts[1])
                    elif line.startswith('FoamDeltaY'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        self.foam_delta_y = float(parts[1])
                    elif line.startswith('FoamDivides'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        self.foam_divides = int(parts[1])
                    elif line.startswith('[foam_'):
                    
                        state = 'body'
                        if not hasattr(self, 'num_foams'):
                            report_func({'ERROR'}, 'NumFoams is not setted')
                            return {'ERROR'}
                            
                        self.foam_elems = [None] * self.num_foams
                        cur_foam = FoamElem()
                        line = line[6:]
                        num = int(line.split(']')[0].strip())
                        self.foam_elems[num] = cur_foam
 
                elif state == 'body':
                    if line.startswith('NumParts'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_num_parts = int(parts[1])
                        cur_points = [None] * int(cur_num_parts)
                    elif line.startswith('Alpha'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_alpha = parts[1]
                    elif line.startswith('Speed'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_speed = parts[1]
                    elif line.startswith('Braking'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_braking = parts[1]
                    elif line.startswith('Appear'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_appear = parts[1]
                    elif line.startswith('TexScaleX'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_tex_scale_x = float(parts[1])
                    elif line.startswith('NumFoams'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_num_foams = int(parts[1])
                    elif line.startswith('Texture'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_texture = parts[1]
                    elif line.startswith('Type'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        parts[1] = parts[1].strip()
                        cur_type_ = int(parts[1])
                        
                    elif line.startswith('[foam_'):
                        cur_foam.set(cur_num_parts, 
                                     cur_alpha,
                                     cur_speed,
                                     cur_braking,
                                     cur_appear,
                                     cur_tex_scale_x,
                                     cur_num_foams,
                                     cur_texture,  
                                     cur_type_,    
                                     cur_points)
                        cur_foam = FoamElem()
                        line = line[6:]
                        num = int(line.split(']')[0].strip())
                        self.foam_elems[num] = cur_foam
                    elif line.startswith('key_'):
                        parts = line.split(sep=';')[0].split(sep='=')
                        
                        point_num = int(parts[0][4:].strip())
                        
                        data = parts[1].split(sep=',')
                        coords = [float(v.strip()) for v in data]
                        
                        matrix_1 = mathutils.Matrix.Translation((coords[0], 0, coords[1]))
                        matrix_1.translation *= mathutils.Vector([-1, 1, 1])
                        matrix_1 = correction_matrix.to_4x4() @ matrix_1
                        
                        matrix_2 = mathutils.Matrix.Translation((coords[2], 0, coords[3]))
                        matrix_2.translation *= mathutils.Vector([-1, 1, 1])
                        matrix_2 = correction_matrix.to_4x4() @ matrix_2
                        cur_points[point_num] = Point(point_num, matrix_1, matrix_2)

                else:
                    report_func({'ERROR'}, 'Unknown state')
        cur_foam.set(cur_num_parts, 
                                     cur_alpha,
                                     cur_speed,
                                     cur_braking,
                                     cur_appear,
                                     cur_tex_scale_x,
                                     cur_num_foams,
                                     cur_texture,  
                                     cur_type_,    
                                     cur_points)          
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
    collection.objects.link(root)
    root['ExportType'] = 'FoamLocation'
    
    foams_locator_name = 'foams'  
    foams_locator = bpy.data.objects.new(foams_locator_name, None)
    collection.objects.link(foams_locator)
    foams_locator.parent = root
    foams_locator['MaxFoamDistance'] = data.max_foam_distance
    foams_locator['FoamDeltaY'] = data.foam_delta_y
    foams_locator['FoamDivides'] = data.foam_divides

    
    for i in range(len(data.foam_elems)):
        locator_name = 'foam_{:04d}'.format(i)
        cur_foam_locator = bpy.data.objects.new(locator_name, None)
        collection.objects.link(cur_foam_locator)
        cur_foam_locator.parent = foams_locator
        

        elem = data.foam_elems[i]
        cur_foam_locator['Alpha'] = elem.alpha
        cur_foam_locator['Speed'] = elem.speed
        cur_foam_locator['Braking'] = elem.braking
        cur_foam_locator['Appear'] = elem.appear
        cur_foam_locator['TexScaleX'] = elem.tex_scale_x
        cur_foam_locator['NumFoams'] = elem.num_foams
        cur_foam_locator['Texture'] = elem.texture
        cur_foam_locator['Type'] = elem.type_

        
        for j in range(len(data.foam_elems[i].points)):
        
            cur_point = data.foam_elems[i].points[j]
            locator_1_name = 'key1_{:04d}'.format(j)
            locator_2_name = 'key2_{:04d}'.format(j)
            
            
            locator_1 = bpy.data.objects.new(locator_1_name, None)
            collection.objects.link(locator_1)
            locator_1.parent = cur_foam_locator
            locator_1.empty_display_type = 'ARROWS'
            locator_1.empty_display_size = 1.0
            locator_1.matrix_basis = cur_point.matrix_1
            
            locator_2 = bpy.data.objects.new(locator_2_name, None)
            collection.objects.link(locator_2)
            locator_2.parent = cur_foam_locator
            locator_2.empty_display_type = 'ARROWS'
            locator_2.empty_display_size = 1.0
            locator_2.matrix_basis = cur_point.matrix_2


    return {'FINISHED'}

class ImportFoamForLoc(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import.foam_for_locations"
    bl_label = "Import foam for locations"

    # ImportHelper mixin class uses this
    filename_ext = ".ini"

    filter_glob: StringProperty(
        default="*.ini",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

   

    def execute(self, context):
        return import_foam(context, self.filepath, report_func=self.report)


def menu_func_import(self, context):
    self.layout.operator(ImportFoamForLoc.bl_idname,
                         text="Foam for loc Import(.ini)")


def register():
    bpy.utils.register_class(ImportFoamForLoc)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportFoamForLoc)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
