bl_info = {
    "name": "SeaDogs Utils",
    "version": (1, 0, 0),
    "blender": (4, 4, 1),
    "category": "Object",
    "support": "COMMUNITY",
    "author": "Wazar",
}

import bmesh
import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty, IntProperty
import numpy
from mathutils import Vector, Matrix
import re
from math import *

foam_depth = 45.0

max_foams = 35

def remove_blender_name_postfix(name):
    return re.sub(r'\.\d{3}', '', name)

def get_foam_object(root):
    root_children = root.children
    foams_locator = None
    for child in root_children:
        if child.type == 'EMPTY' and remove_blender_name_postfix(child.name) == 'foams':
            foams_locator = child
            break
            
    if foams_locator is None:
        collection = root.users_collection[0]
        foams_locator_name = 'foams'  
        foams_locator = bpy.data.objects.new(foams_locator_name, None)
        collection.objects.link(foams_locator)
        foams_locator.parent = root
        foams_locator['MaxFoamDistance'] = 1000
        foams_locator['FoamDeltaY'] = 0.2
        foams_locator['FoamDivides'] = 4
        
        
    return foams_locator


def create_new_foam(foam_object):
    collection = foam_object.users_collection[0]
    
    locator_name = 'foam_{:04d}'.format(len(foam_object.children))
    cur_foam_locator = bpy.data.objects.new(locator_name, None)
    collection.objects.link(cur_foam_locator)
    cur_foam_locator.parent = foam_object
    cur_foam_locator['Alpha'] = '148, 196'
    cur_foam_locator['Speed'] = '0.200, 0.250'
    cur_foam_locator['Braking'] = '0.000, 0.000'
    cur_foam_locator['Appear'] = '0.000, 0.000'
    cur_foam_locator['TexScaleX'] = 0.100
    cur_foam_locator['NumFoams'] = 2
    cur_foam_locator['Texture'] = 'foam.tga'
    cur_foam_locator['Type'] = 2
    
    
    
    return cur_foam_locator
    
    
def add_key_to_foam(foam, vert, shift):
    collection = foam.users_collection[0]
    
    cur_index = len(foam.children) // 2
    
    base = vert.coord.to_2d()
    norm = vert.get_direction()

    
    shift_1 = 0
    shift_2 = foam_depth
    
    if shift == 'near':
        shift_1 -= foam_depth / 3
        shift_2 -= foam_depth / 3
    elif shift == 'far':
        shift_1 += foam_depth / 3
        shift_2 += foam_depth / 3
    

    shift_1_vec = norm.normalized() * shift_1
    shift_2_vec = norm.normalized() * shift_2
    
    coord_1 = base + shift_1_vec
    coord_2 = base + shift_2_vec
    
    locator_1_name = 'key1_{:04d}'.format(cur_index)
    locator_2_name = 'key2_{:04d}'.format(cur_index)
    
    
    locator_1 = bpy.data.objects.new(locator_1_name, None)
    collection.objects.link(locator_1)
    locator_1.parent = foam
    locator_1.empty_display_type = 'ARROWS'
    locator_1.empty_display_size = 1.0
    locator_1.matrix_basis = Matrix.Translation(coord_1.to_3d())
    
    locator_2 = bpy.data.objects.new(locator_2_name, None)
    collection.objects.link(locator_2)
    locator_2.parent = foam
    locator_2.empty_display_type = 'ARROWS'
    locator_2.empty_display_size = 1.0
    locator_2.matrix_basis = Matrix.Translation(coord_2.to_3d())
    





def vert_to_string(v):
    return '{:.10f}:{:.10f}:{:.10f}'.format(v.co.x, v.co.y, v.co.z)

class Point:
    def __init__(self, number, coord, normal, _points):
        self.number = number
        self.coord = coord
        self.normal = normal
        self.edges = []
        self.passed = 0
        self._points = _points

    def set_pairs(self, pairs):
        cur_pairs = set(self.edges)
        new_pairs = set(pairs)

        self.edges = list(cur_pairs.union(new_pairs))

        for cur in pairs:
            if cur == self.number:
                bpy.context.scene.cursor.location = self.coord
                raise ValueError('{} is setted as pair to itself'.format(cur))
            
    def add_pair(self, pair):
        cur_pairs = set(self.edges)
        cur_pairs.add(pair)
        self.edges = list(cur_pairs)


    def get_direction(self):

        edge_1 = self._points[self.edges[0]].coord.to_2d() - self.coord.to_2d()
        edge_2 = None
        if (len(self.edges) > 1):
            edge_2= self._points[self.edges[1]].coord.to_2d() - self.coord.to_2d()
        else:
            edge_2 = -edge_1
        

        norm = edge_1.normalized() + edge_2.normalized()
        if norm.length == 0.0:
           norm = edge_1.orthogonal()

        if norm.dot(self.normal.to_2d()) < 0:
            norm = -norm
        return norm
    
    def print(self):
        print('{}: ({}) => {}'.format(self.number, self.coord, self.edges))



class SubGraph:
    def __init__(self, points, is_cycle):
        self.points = points
        self.is_cycle = is_cycle


    def print(self):
        print('{}; is_cycle: {}'.format([p.number for p in self.points], self.is_cycle))


def get_sub_graphs(context, mesh, report):
    points = {}
    point_nums = []
    coord_idx = {}
    alias_idx = {}
    sub_graphs = []


    bm = bmesh.from_edit_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    print(len(bm.verts[:]))
    print(len(bm.edges[:]))

    for i, v in enumerate(bm.verts):
        v.index = i

    for i, v in enumerate(bm.verts):
        if not v.select:
            continue
        cur_idx = v.index

        if cur_idx in alias_idx:
           cur_idx = alias_idx[cur_idx]
        else:
            vstr = vert_to_string(v)
            if vstr in coord_idx:
                cur_idx = coord_idx[vstr]
                alias_idx[v.index] = cur_idx
            else:
                coord_idx[vstr] = cur_idx
                alias_idx[cur_idx] = cur_idx
                point_nums.append(cur_idx)
                cur_point = Point(cur_idx, v.co.copy(), v.normal.copy(), points)
                points[cur_idx] = cur_point

    point_nums.sort()

    for i, v in enumerate(bm.verts):
        if not v.select:
            continue
        cur_idx = alias_idx[v.index]

        cur_point = points[cur_idx]
            
            

        pairs = [e.other_vert(v) for e in v.link_edges if e.other_vert(v).select]
        pair_idxs = [alias_idx[p.index] for p in pairs if alias_idx[p.index] != cur_idx]
        cur_point.set_pairs(pair_idxs)
        if (len(cur_point.edges) > 2):
            report({'ERROR'}, '{}: vertex with more than two selected edges is selected'.format(cur_idx))
            context.scene.cursor.location = v.co
            return sub_graphs
        

        if (len(cur_point.edges) == 0):
            report({'ERROR'}, '{}: vertex without selected edges is selected'.format(cur_idx))
            context.scene.cursor.location = v.co
            return sub_graphs
    
        
        for p in pair_idxs:
            pair_point = points[p]
            pair_point.add_pair(cur_idx)
            if (len(pair_point.edges) > 2):
                report({'ERROR'}, '{}: vertex with more than two selected edges is selected'.format(p))
                context.scene.cursor.location = pair_point.coord
                return sub_graphs


    #print('=======P======')
    #for idx in point_nums:
    #    cur_point = points[idx]
    #    cur_point.print()
    #print('==================')


    for idx in point_nums:
        cur_point = points[idx]
        print('cur_point = {}; passed = {}'.format(idx, cur_point.passed))
        if cur_point.passed != 0:
            continue

        start_point = cur_point
        cur_point.passed = 1
        prev_point = cur_point

        is_cycle = False
        cur_indexes = [cur_point.number]
        print('start {}'.format(cur_point.number))
        while True:
            next_idx = cur_point.edges[0]
            if next_idx == prev_point.number:
                if len(cur_point.edges) > 1:
                    next_idx = cur_point.edges[1]
                else:
                    print('cur_point.number = {}; prev_point.number = {} no next'.format(cur_point.number, prev_point.number))
                    break
            next_point = points[next_idx]
            print('next_point.number = {}; cur_point.number = {} ->'.format(next_point.number, cur_point.number))    
            cur_indexes.append(next_idx)
            if (next_point.passed == 1):
                is_cycle = True
                print('cur_point.number = {}; prev_point.number = {} cycle'.format(next_point.number, cur_point.number))
                break
            prev_point = cur_point
            cur_point = next_point
            cur_point.passed = 1

        if not is_cycle:
            prev_points = []

            if len(start_point.edges) > 1:
                prev_point = start_point
                next_idx = start_point.edges[1]
                cur_point = points[next_idx]

                while True:
                    next_idx = cur_point.edges[0]
                    print('next_idx = {}; prev_point.number = {}'.format(next_idx, prev_point.number))
                    if next_idx == prev_point.number:
                        if len(cur_point.edges) > 1:
                            next_idx = cur_point.edges[1]
                        else:
                            break
                    prev_point = cur_point
                    cur_point = points[next_idx]

                prev_points = [cur_point.number]
                prev_point = cur_point
                cur_point.passed = 1

                while True:
                    next_idx = cur_point.edges[0]
                    if next_idx == prev_point.number:
                        next_idx = cur_point.edges[1]
                    next_point = points[next_idx]
                    if (next_point.passed == 1):
                        break
                    prev_points.append(next_idx)
                    prev_point = cur_point
                    cur_point = next_point
                    cur_point.passed = 1

                prev_points.extend(cur_indexes)
                cur_indexes = prev_points
        

        point_for_graph = [points[i] for i in cur_indexes]
        cur_graph = SubGraph(point_for_graph, is_cycle)


        sub_graphs.append(cur_graph)


    #print('=====SG======')
    #for sg in sub_graphs:
    #    sg.print()
    #print('==================')
    return sub_graphs

def generate_foam(context, mesh, root, shift, report):
    sub_graphs = get_sub_graphs(context, mesh, report)
    foam_object = get_foam_object(root)

    for sg in sub_graphs:
        cur_foam = create_new_foam(foam_object)
        count = 0
        for i, v in enumerate(sg.points): 

            add_key_to_foam(cur_foam, v, shift)
            if count > max_foams and i < len(sg.points) - 2:
                count = 0
                print_foam_links(cur_foam, report)
                cur_foam = create_new_foam(foam_object)
                add_key_to_foam(cur_foam, v, shift)
            count += 1
        print_foam_links(cur_foam, report)
         




def print_foam_links(foam, report):
    point_locators = []
    points = []
    for child in foam.children:
        if child.type == 'EMPTY':
            point_locators.append(child)

    if len(point_locators) % 2 == 1:
        report({'ERROR'}, 'point count should be even for locator "{}"'.format(foam.name))
        return {'CANCELLED'}
        
    key_count = len(point_locators) // 2

    
    for i in range(key_count):
        p = point_locators[i]

        points.append([p, 0, point_locators[i+key_count]])

    for i in range(key_count - 1):
        point_locators[key_count + i].constraints.clear()
        constraint = point_locators[key_count + i].constraints.new(type='TRACK_TO')
        constraint.target = point_locators[key_count + i + 1]
        constraint.name = 'link_{}_f'.format(i)
        constraint = point_locators[key_count + i].constraints.new(type='TRACK_TO')
        constraint.target = point_locators[i]
        constraint.name = 'link_{}_s'.format(i)

    i = key_count - 1
    constraint = point_locators[key_count + i].constraints.new(type='TRACK_TO')
    constraint.target = point_locators[i]
    constraint.name = 'link_{}_s'.format(i) 



def GenerateFoam(shift):   
    class GenerateFoamImpl(bpy.types.Operator):
        bl_idname = "seadogs_util.generate_foam_"+shift
        bl_label = "Generate foam ({})".format(shift)
        bl_options = {'REGISTER', 'UNDO'}

        @classmethod
        def poll(cls, context):
            return bpy.context.active_object != None and bpy.context.active_object.mode == 'EDIT'

        def execute(self, context):
            scene = context.scene
            cursor = scene.cursor.location
            mesh_object = bpy.context.view_layer.objects.active

            selected_objects = [o for o in bpy.context.view_layer.objects.selected if o.name != mesh_object.name]
            
            
            if (len(selected_objects) != 1 or remove_blender_name_postfix(selected_objects[0].name) != 'root' or selected_objects[0].type != 'EMPTY'):
                self.report({'ERROR'}, 'Root of foam collection should be selected');
                return {'CANCELLED'}
                
            root_for_foam = selected_objects[0]

            ret = generate_foam(context, mesh_object, root_for_foam, shift, self.report)
            if ret is not None:
                return {'CANCELLED'}

            return {'FINISHED'}
   
    return GenerateFoamImpl





locator_to_bone = {
    'danny': {
        'camera': 16, 
        'fonar_belt': 2, 
        'lantern_belt': 2, 
        'hat': 16, 
        'gun_belt': 2, 
        'gun_hand': 70, 
        'mush_belt': 7, 
        'mush_hand': 69, 
        'saber_belt': 2, 
        'saber_hand': 69
    },
    'man': {
        'camera': 16, 
        'fonar_belt': 1, 
        'lantern_belt': 1, 
        'hat': 16, 
        'gun_belt': 7, 
        'gun_hand': 66, 
        'mush_belt': 2, 
        'mush_hand': 65, 
        'saber_belt': 7, 
        'saber_hand': 65
    }
}


def change_bone_for_locator(locator, char, bone_num):
    print('1. bone_num: {}'.format(bone_num))
    parent_bone = 'Bone{}'.format(bone_num)
    print('2. parent_bone: {}'.format(parent_bone))
    if locator.parent_bone == parent_bone:
        return

    arma = char.armature_obj

    bpy.ops.object.select_all(action='DESELECT')
    arma.select_set(True)
    bpy.context.view_layer.objects.active = arma 

    bpy.ops.object.mode_set(mode='EDIT')

    bone_obj = arma.data.edit_bones[parent_bone]
    for c in arma.data.edit_bones:
        c.select = False
    bone_obj.select = True
    arma.data.edit_bones.active = bone_obj

    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    locator.select_set(True)
    arma.select_set(True)
    bpy.context.view_layer.objects.active = arma

    bpy.ops.object.parent_set(type='BONE', keep_transform=True)
    print('locator {}, par {}'.format(locator.name, locator.parent_bone))

def fix_locators(root, reference_root, skeleton, report):
    bone_map = locator_to_bone[skeleton]
    for loc_name, bone_idx in bone_map.items():
        locator = getattr(root, loc_name)
        if locator is None:
            locator = bpy.data.objects.new(loc_name, None)
            root.collection.objects.link(locator)
            locator.parent = root.root
            setattr(root, loc_name, locator)

        change_bone_for_locator(locator, root, bone_idx)
        ref_locator = getattr(reference_root, loc_name)
        if ref_locator is None or ref_locator.hide_render:
            continue
        locator.matrix_world = ref_locator.matrix_world.copy()


class Character:
    def __init__(self, root):
        print('init {}'.format(root.name))
        self.root = root
        self.collection = root.users_collection[0]
        armature_obj = None
        for child in root.children:
            if remove_blender_name_postfix(child.name) == 'armature_obj' and child.type == 'ARMATURE':
                if armature_obj is None:
                    armature_obj = child
                else:
                    raise ValueError('duplicate armature_obj for {}'.format(root.name))
                

        if armature_obj is None:
            raise ValueError('armature_obj not found for {}'.format(root.name))
        
        self.armature_obj = armature_obj



        attributes = set(('camera', 'fonar_belt', 'gun_belt', 'gun_hand', 'hat', 'lantern_belt', 'mush_belt', 'mush_hand', 'saber_belt', 'saber_hand'))


        for a in attributes:
            setattr(self, a, None)

        for child in armature_obj.children:
            name = remove_blender_name_postfix(child.name).lower()

            if name not in attributes:
                continue
            print('add loc {}; parent_bone: {}; renderable {}'.format(name, child.parent_bone, not child.hide_render))
            if getattr(self, name) is not None:
                raise ValueError('duplicate {} for {}'.format(name, root.name))
            setattr(self, name, child)

        bones = {}

        root_bone = armature_obj.data.bones[0]
        bones[0] = root_bone
        bones_list = root_bone.children_recursive

        for bone in bones_list:

            if not bone.name.startswith('Bone'):
                raise ValueError('Wrong name "{}" for bone'.format(name))
            num = int(bone.name[4:])
            if num in bones:
                raise ValueError('Duplicate bone {} for {}'.format(num, root.name))
            print('bone: {} with num: {}'.format(bone.name, num))
            bones[num] = bone
                        

def FixLocators(skeleton):   
    class FixLocatorsImpl(bpy.types.Operator):
        bl_idname = "seadogs_util.fix_locators_"+skeleton
        bl_label = "Fix locators ({})".format(skeleton)
        bl_options = {'REGISTER', 'UNDO'}
        
        def execute(self, context):

            reference_root = bpy.context.view_layer.objects.active
            selected_objects = [o for o in bpy.context.view_layer.objects.selected if o.name != reference_root.name]
            
            
            if (len(selected_objects) == 0 or remove_blender_name_postfix(selected_objects[0].name) != 'root' or selected_objects[0].type != 'EMPTY'):
                self.report({'ERROR'}, 'Roots for fixing should be selected')
                return {'CANCELLED'}
                
            for s in selected_objects:
                if (remove_blender_name_postfix(s.name) != 'root' or s.type != 'EMPTY'):
                    self.report({'ERROR'}, 'Selected not-root object "{}"'.format(s.name))
                    return {'CANCELLED'}

            ref_char = Character(reference_root)
            for s in selected_objects:
                sel = Character(s)
                ret = fix_locators(sel, ref_char, skeleton, self.report)
                if ret is not None:
                    return {'CANCELLED'}


            return {'FINISHED'}   
    return FixLocatorsImpl

class SeadogsProperties(bpy.types.PropertyGroup):
    #todo options
    pass





class MAIN_PT_SeadogsUtils:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Seadogs Utils"


class SETUP_PT_SeadogsUtils(MAIN_PT_SeadogsUtils, bpy.types.Panel):
    bl_label = "Seadogs tools"
    bl_idname = "SETUP_PT_SeadogsUtils"
    bl_icon = {'TOOL_SETTINGS'}

    def draw_header(self, context):
        # Example property to display a checkbox, can be anything
        self.layout.label(text="", icon="MOD_OCEAN")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        seadogs_tool = scene.seadogs_tool

        row = layout.row()
        row.label(text = "Foam utils")


        row = layout.row()
        colL = row.column(align=False)
        colR = row.column(align=False)
        colL.operator("seadogs_util.generate_foam_near")
        colR.operator("seadogs_util.generate_foam_far")

        layout.row().separator()


        row = layout.row()
        row.label(text = "Character util")


        row = layout.row()
        colL = row.column(align=False)
        colR = row.column(align=False)
        colL.operator("seadogs_util.fix_locators_man")
        colR.operator("seadogs_util.fix_locators_danny")










classes = (
    SeadogsProperties,
    SETUP_PT_SeadogsUtils,
    GenerateFoam('near'),
    GenerateFoam('far'),
    FixLocators('man'),
    FixLocators('danny')
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.Scene.seadogs_tool = PointerProperty(type=SeadogsProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        
    del bpy.types.Scene.seadogs_tool



if __name__ == "__main__":
    register()