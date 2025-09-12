bl_info = {
    "name": "SeaDogs Utils",
    "version": (0, 0, 5),
    "blender": (4, 4, 1),
    "category": "Object",
    "support": "COMMUNITY",
    "author": "Wazar",
}

import bmesh
import bpy
import numpy
from mathutils import Vector, Matrix
import re
from math import *

vertex_smooth_mark_name = 'vertex_smooth_mark'

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
    
    base = vert[0]
    norm = vert[1]
    base.z = 0
    norm.z = 0
    
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
    locator_1.matrix_basis = Matrix.Translation(coord_1)
    
    locator_2 = bpy.data.objects.new(locator_2_name, None)
    collection.objects.link(locator_2)
    locator_2.parent = foam
    locator_2.empty_display_type = 'ARROWS'
    locator_2.empty_display_size = 1.0
    locator_2.matrix_basis = Matrix.Translation(coord_2)
    


def get_vert_list(mesh, report):
    depsgraph = bpy.context.evaluated_depsgraph_get()


    #ob = bpy.context.object
    #assert ob.type == "MESH"
    #me = ob.data
    #bm2 = bmesh.new()
    bm = bmesh.from_edit_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    print(len(bm.verts[:]))
    print(len(bm.edges[:]))
    
    v0 = bm.select_history.active
    iv0 = None
    
    if v0 is None:
        report({'ERROR'}, 'Start vertex should be selected')
        bm.free()
        return None
    fx = bmesh.ops.contextual_create(
            bm,
            geom=bm.verts[:] + bm.edges[:],
            )
    f = fx["faces"][0]
    
    fverts = f.verts[:]
    
    if f.normal.dot((0, 0, 1)) < 0:
        fverts.reverse()
    #bm.faces.remove(f)
    print(v0)
    for i, v in enumerate(fverts):
        #print(v)
        v.index = i
        if v.co == v0.co:
            iv0 = i

    if iv0 is None:
        report({'ERROR'}, 'Start vertex should be re-selected')
        
        bm.faces.remove(f)
        bm.free()
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
        return None

    verts = [None] * len(fverts)
    for v in fverts:
        v.index = (v.index - iv0) % len(fverts) 
        verts[v.index] = v
       
    #verts = bm.verts[:]
    #verts.sort()

    coords = [[v.co, v.normal] for v in verts if v.select]
    coords.append(coords.pop(0))

    #bm.verts.remove(f)
    edges = f.edges[:]
    print("edges = ", f.edges[:])
    bm.edges.ensure_lookup_table()
    
    #bm.edges.remove(f.edges[:])
    bm.faces.remove(f)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.free()
    
    #bpy.ops.object.mode_set( mode = 'OBJECT' ) 
    
    
    selected = [v for v in mesh.data.vertices if v.select]
    
    
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)

    bpy.ops.mesh.select_all(action = 'DESELECT')
    #bpy.ops.object.mode_set(mode = 'OBJECT')
    #for v in selected:
    #    v.select = True
    #bpy.ops.object.mode_set(mode = 'EDIT') 

    #bmesh.update_edit_mesh(mesh.data) 
    print("fx: ", fx)
    return coords



def generate_foam(mesh, root, shift, report):
    
    

    #mesh_data = mesh.data
    #selected_verts = list(filter(lambda v: v.select, mesh_data.vertices))


    vert_list = get_vert_list(mesh, report)

    

    print(vert_list)
    
    
    prev = None
    foam_object = get_foam_object(root)
    cur_foam = create_new_foam(foam_object)
    count = 0
    for i, v in enumerate(vert_list): 
        if prev is not None and prev[0] == v[0]:
            continue
        add_key_to_foam(cur_foam, v, shift)
        if count > max_foams and i < len(vert_list) - 2:
            count = 0
            cur_foam = create_new_foam(foam_object)
            add_key_to_foam(cur_foam, v, shift)
        prev = v
        count += 1
         






def sort_foam_points(root, foam, report):
    print('sort: {}'.format(foam.name))
    collection = root.users_collection[0]


    point_locators = []

    points = []
    for child in foam.children:
        if child.type == 'EMPTY':
            point_locators.append(child)

    if len(point_locators) % 2 == 1:
        report({'ERROR'}, 'point count should be even for locator "{}"'.format(foam.name))
        return {'CANCELLED'}
        
    key_count = len(point_locators) // 2
    
    
    max_x = None
    min_x = None
    max_y = None
    min_y = None
    
    
    
    for i in range(key_count):
        p = point_locators[i]
        coord = p.matrix_world.translation
        if max_x is None or max_x[1] < coord.x:
            max_x = (p, coord.x)
            
        if max_y is None or max_y[1] < coord.y:
            max_y = (p, coord.y)
            
        if min_x is None or min_x[1] > coord.x:
            min_x = (p, coord.x)
            
        if min_y is None or min_y[1] > coord.y:
            min_y = (p, coord.y)

        points.append([p, 0, point_locators[i+key_count]])



    
    mid_x = (max_x[1] + min_x[1]) * 0.5
    mid_y = (max_y[1] + min_y[1]) * 0.5
    
    diff_x = max_x[1] - min_x[1]
    diff_y = max_y[1] - min_y[1]
    
    mid_vec = Vector((mid_x, mid_y, 0))
    mid_vec_2d = mid_vec.resized(2)

    scale_vec = Vector((diff_x, diff_y, 1))

    bpy.ops.mesh.primitive_cube_add(
        size=1, 
        enter_editmode=False, 
        align='WORLD', 
        location=mid_vec, 
        rotation=(0, 0, 0), 
        scale=scale_vec)
        
        
    bounds_cube = bpy.context.object
    bounds_cube.name = 'bounds_'+remove_blender_name_postfix(foam.name)
    bounds_cube.parent = root
    #collection.objects.link(bounds_cube)
    
    for i in range(key_count - 1):
        point_locators[key_count + i].constraints.clear()
        constraint = point_locators[key_count + i].constraints.new(type='TRACK_TO')
        constraint.target = point_locators[key_count + i + 1]
        constraint.name = 'link_{}_f'.format(i)
        constraint = point_locators[key_count + i].constraints.new(type='TRACK_TO')
        constraint.target = point_locators[i]
        constraint.name = 'link_{}_s'.format(i)
    
    if 'NeedSort' not in foam or not foam['NeedSort']:
        foam['NeedSort'] = False
        if 'BasicVector' not in foam:
            foam['BasicVector'] = [1.0, 0.0]
        return None
    basic_vec = Vector((1, 0))
    
    if 'BasicVector' in foam:
        basic_vec = Vector(foam['BasicVector'][0:2])
    
    print('sort({})'.format(foam.name))
    
    basic_vec = basic_vec.normalized()
    basic_vec *= -1
    print('\t\t basic_vec={}'.format([basic_vec.x, basic_vec.y]))
    
    for p in points:
        point_2d = p[0].matrix_world.translation
        point_2d = Vector((point_2d.x, point_2d.y))
        vec = (point_2d -  mid_vec_2d).normalized()
        
        print('\t point={} vec1={}'.format(p[0].name, p[0].matrix_world.translation))
        print('\t point={} rszd={}'.format(p[0].name, vec))
        
        p[1] = basic_vec.angle_signed(vec)
        print('\t point={} angle={}'.format(p[0].name, p[1]))
        
        diff = (point_2d -  mid_vec_2d)
        print('\t\t vec={}; non-norm = {}'.format([vec.x, vec.y], [diff.x, diff.y]))
        
    
    
    
    points.sort(key=lambda p : p[1])
    for i, p in enumerate(points): 
        p[0].name = 'key1_{:04d}'.format(i)
        p[2].name = 'key2_{:04d}'.format(i)
        
    for i in range(key_count - 1):
        points[i][2].constraints.clear()
        constraint = points[i][2].constraints.new(type='TRACK_TO')
        constraint.target = points[i+1][2]
        constraint.name = 'link_{}_f'.format(i)
        constraint = points[i][2].constraints.new(type='TRACK_TO')
        constraint.target = points[i][0]
        constraint.name = 'link_{}_s'.format(i)
    return None
    


def sort_foams(root, report):
    collection = root.users_collection[0]
    root_children = root.children[:]

    for child in root_children:
        if child.type == 'EMPTY' and remove_blender_name_postfix(child.name) == 'foams':
            foams_locator = child
            for child in foams_locator.children:
                if child.type == 'EMPTY':
                    ret = sort_foam_points(root, child, report)
                    if ret != None:
                        return ret
                    
        elif remove_blender_name_postfix(child.name).startswith('bounds_'):
            bpy.data.objects.remove(child)
            
    return None
            
   

class SeaDogsMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_seadogs_utils"
    bl_label = "SeaDogs Utils"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.select_all", text="Select/Deselect All").action = 'TOGGLE'


class MarkToSmoothNormals(bpy.types.Operator):
    bl_idname = "object.mark_smooth_normals"
    bl_label = "Mark normals to smooth"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        cursor = scene.cursor.location
        obj = bpy.context.view_layer.objects.active
        
        mesh = obj.data
        
        attribute = mesh.attributes.get(vertex_smooth_mark_name)
        if attribute is None:
            attribute = mesh.attributes.new(name=vertex_smooth_mark_name, type="BOOLEAN", domain="POINT")

        bm = bmesh.from_edit_mesh(mesh)
        layer = bm.verts.layers.bool.get(vertex_smooth_mark_name)

        for vert in bm.verts:  
            if vert.select:
                vert[layer] = True

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}


class UnMarkToSmoothNormals(bpy.types.Operator):
    bl_idname = "object.unmark_smooth_normals"
    bl_label = "Unmark normals to smooth"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        cursor = scene.cursor.location
        obj = bpy.context.view_layer.objects.active
        
        mesh = obj.data
        
        attribute = mesh.attributes.get(vertex_smooth_mark_name)
        if attribute is None:
            attribute = mesh.attributes.new(name=vertex_smooth_mark_name, type="BOOLEAN", domain="POINT")
        
        
        
        bm = bmesh.from_edit_mesh(mesh)
        layer = bm.verts.layers.bool.get(vertex_smooth_mark_name)

        for vert in bm.verts:
            print(f"Previous value for {vert} : {vert[layer]}")
            
            if vert.select:
                print(f"SELECTED {vert}")
                vert[layer] = False
            
            print(f"New value for {vert} : {vert[layer]}")

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}
        
      

gen_foam_classes = {}

      
def GenerateFoam(shift):   
    if shift in gen_foam_classes:
        return gen_foam_classes[shift]
    class GenerateFoamImpl(bpy.types.Operator):
        bl_idname = "object.generate_foam_"+shift
        bl_label = "Generate foam ({})".format(shift)
        bl_options = {'REGISTER', 'UNDO'}

        def execute(self, context):
            scene = context.scene
            cursor = scene.cursor.location
            mesh_object = bpy.context.view_layer.objects.active

            selected_objects = [o for o in bpy.context.view_layer.objects.selected if o.name != mesh_object.name]
            
            
            if (len(selected_objects) != 1 or remove_blender_name_postfix(selected_objects[0].name) != 'root' or selected_objects[0].type != 'EMPTY'):
                self.report({'ERROR'}, 'Root of foam collection should be selected');
                return {'CANCELLED'}
                
            root_for_foam = selected_objects[0]

            ret = generate_foam(mesh_object, root_for_foam, shift, self.report)
            if ret is not None:
                return {'CANCELLED'}

            return {'FINISHED'}
            
    gen_foam_classes[shift] = GenerateFoamImpl       
    return GenerateFoamImpl


class SortFoams(bpy.types.Operator):
    bl_idname = "object.sort_foams"
    bl_label = "Sort foams"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        cursor = scene.cursor.location
        root_object = bpy.context.view_layer.objects.active

        if (remove_blender_name_postfix(root_object.name) != 'root' or root_object.type != 'EMPTY'):
            self.report({'ERROR'}, 'Root of foam collection should be selected');
            return {'CANCELLED'}

        ret = sort_foams(root_object, self.report)
        if ret is not None:
            return {'CANCELLED'}
    
        return {'FINISHED'}
    

fix_locator_classes = {}





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
    if skeleton in fix_locator_classes:
        return fix_locator_classes[skeleton]
    class FixLocatorsImpl(bpy.types.Operator):
        bl_idname = "object.fix_locators_"+skeleton
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
    fix_locator_classes[skeleton] = FixLocatorsImpl       
    return FixLocatorsImpl


def menu_func_sm(self, context):
    self.layout.operator(MarkToSmoothNormals.bl_idname)
    
def menu_func_usm(self, context):
    self.layout.operator(UnMarkToSmoothNormals.bl_idname)
    
    
def menu_func_generate_foam(shift):
    def _menu_func_generate_foam(self, context):
        self.layout.operator(GenerateFoam(shift).bl_idname)
    return _menu_func_generate_foam
    
def menu_func_sort_foams(self, context):
    self.layout.operator(SortFoams.bl_idname)
    

def menu_func_fix_locators(skeleton):
    def _menu_func_fix_locators(self, context):
        self.layout.operator(FixLocators(skeleton).bl_idname)
    return _menu_func_fix_locators

addon_keymaps = []


def register():


    bpy.utils.register_class(MarkToSmoothNormals)
    bpy.utils.register_class(UnMarkToSmoothNormals)
    bpy.utils.register_class(GenerateFoam('near'))
    bpy.utils.register_class(GenerateFoam('far'))
    bpy.utils.register_class(SortFoams)
    bpy.utils.register_class(FixLocators('man'))
    bpy.utils.register_class(FixLocators('danny'))
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func_sm)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func_usm)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func_generate_foam('near'))
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func_generate_foam('far'))
    bpy.types.VIEW3D_MT_object.append(menu_func_sort_foams)
    bpy.types.VIEW3D_MT_object.append(menu_func_fix_locators('man'))
    bpy.types.VIEW3D_MT_object.append(menu_func_fix_locators('danny'))
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='Smooth normals', space_type='EMPTY')
        kmi = km.keymap_items.new(MarkToSmoothNormals.bl_idname, 'S', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(UnMarkToSmoothNormals.bl_idname, 'U', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(GenerateFoam('near').bl_idname, 'F', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(GenerateFoam('far').bl_idname, 'N', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))

def unregister():
    # Note: when unregistering, it's usually good practice to do it in reverse order you registered.
    # Can avoid strange issues like keymap still referring to operators already unregistered...
    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    bpy.types.VIEW3D_MT_object.remove(menu_func_fix_locators('danny'))
    bpy.types.VIEW3D_MT_object.remove(menu_func_fix_locators('man'))
    bpy.types.VIEW3D_MT_object.remove(menu_func_sort_foams)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func_generate_foam('far'))
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func_generate_foam('near'))
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func_usm)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func_sm)

    bpy.utils.unregister_class(FixLocators('danny'))
    bpy.utils.unregister_class(FixLocators('man'))
    bpy.utils.unregister_class(SortFoams)
    bpy.utils.unregister_class(GenerateFoam('far'))
    bpy.utils.unregister_class(GenerateFoam('near'))
    
    bpy.utils.unregister_class(UnMarkToSmoothNormals)
    bpy.utils.unregister_class(MarkToSmoothNormals)


if __name__ == "__main__":
    register()