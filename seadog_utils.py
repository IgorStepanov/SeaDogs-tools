bl_info = {
    "name": "SeaDogs Utils",
    "version": (1, 1, 0),
    "blender": (4, 4, 1),
    "category": "Object",
    "support": "COMMUNITY",
    "author": "Wazar",
}

import bmesh
import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty, IntProperty, FloatProperty
import numpy
import sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import re
import random
from math import *

foam_depth = 60.0

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


def get_points_object(root):
    root_children = root.children
    locator = None
    for child in root_children:
        if child.type == 'EMPTY' and remove_blender_name_postfix(child.name) == 'points':
            locator = child
            break
    return locator


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
    
    
def add_key_to_foam(foam, vert, shift, seadogs_tool):
    collection = foam.users_collection[0]
    inverted = seadogs_tool.foam_inverted
    cur_depth = seadogs_tool.foam_depth
    cur_index = len(foam.children) // 2
    
    base = vert.coord.to_2d()
    norm = vert.get_direction()
    
    shift_1 = cur_depth
    shift_2 = 0

    if inverted:
        shift_1 = 0
        shift_2 = cur_depth
    
    if shift == 'near':
        shift_1 -= 10
        shift_2 -= 10
    elif shift == 'far':
        shift_1 += 7.8
        shift_2 += 7.8
    elif shift == 'farthest':
        shift_1 += 9.6
        shift_2 += 9.6
    

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

    print('=======P======')
    for idx in point_nums:
        cur_point = points[idx]
        cur_point.print()
    print('==================')

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

        for p in pair_idxs:
            pair_point = points[p]
            pair_point.add_pair(cur_idx)
            if (len(pair_point.edges) > 2):
                report({'ERROR'}, '{}: vertex with more than two selected edges is selected'.format(p))
                context.scene.cursor.location = pair_point.coord
                return sub_graphs

    for idx in point_nums:
        cur_point = points[idx]
        if (len(cur_point.edges) == 0):
            report({'ERROR'}, '{}: vertex without selected edges is selected'.format(cur_idx))
            context.scene.cursor.location = v.co
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

def generate_foam(context, mesh, root, shift, seadogs_tool, report):
    sub_graphs = get_sub_graphs(context, mesh, report)
    foam_object = get_foam_object(root)

    for sg in sub_graphs:
        cur_foam = create_new_foam(foam_object)
        count = 0
        for i, v in enumerate(sg.points): 

            add_key_to_foam(cur_foam, v, shift, seadogs_tool)
            if count > max_foams and i < len(sg.points) - 2:
                count = 0
                print_foam_links(cur_foam, report)
                cur_foam = create_new_foam(foam_object)
                add_key_to_foam(cur_foam, v, shift, seadogs_tool)
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
        constraint = point_locators[i].constraints.new(type='TRACK_TO')
        constraint.target = point_locators[i + 1]
        constraint.name = 'link_{}_n'.format(i)
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
            seadogs_tool = context.scene.seadogs_tool
            mesh_object = bpy.context.view_layer.objects.active

            selected_objects = [o for o in bpy.context.view_layer.objects.selected if o.name != mesh_object.name]
            
            
            if (len(selected_objects) != 1 or remove_blender_name_postfix(selected_objects[0].name) != 'root' or selected_objects[0].type != 'EMPTY'):
                self.report({'ERROR'}, 'Root of foam collection should be selected');
                return {'CANCELLED'}
                
            root_for_foam = selected_objects[0]

            ret = generate_foam(context, mesh_object, root_for_foam, shift, seadogs_tool, self.report)
            if ret is not None:
                return {'CANCELLED'}

            return {'FINISHED'}
   
    return GenerateFoamImpl



def create_random_point(foam_root, bounds, bvh_tree, num):
    seadogs_tool = bpy.context.scene.seadogs_tool
    max_range = seadogs_tool.path_point_max_range
    x_min, x_max, y_min, y_max = bounds
    x_min -= max_range
    y_min -= max_range

    x_max += max_range
    y_max += max_range


    src_point = None
    while True:

        src_point = Vector((random.uniform(x_min, x_max), random.uniform(y_min, y_max), -100))
        direction = Vector((0, 0, 1))

        hit_location, hit_normal, face_index, distance = bvh_tree.ray_cast(src_point, direction)
        if hit_location is None:
            break

    src_point[2] = 0
    locator_name = 'pnt{:04d}'.format(num)
    collection = foam_root.users_collection[0]
    locator = bpy.data.objects.new(locator_name, None)
    collection.objects.link(locator)
    locator.parent = foam_root
    locator.empty_display_type = 'ARROWS'
    locator.empty_display_size = 0.5
    locator.matrix_basis = Matrix.Translation(src_point)



def check_accessible(src, dst, bvh_tree):

    src_point = src.matrix_world.translation.copy()
    dst_point = dst.matrix_world.translation.copy()

    src_point[2] = 0.1
    dst_point[2] = 0.1

    direction = dst_point - src_point
    direction_norm = direction.normalized()
    direction_length = direction.length
    hit_location, hit_normal, face_index, distance = bvh_tree.ray_cast(src_point, direction_norm, direction_length)
    if hit_location is None:
        return True

    return False


def create_path(src, dst, num):
    src_name = remove_blender_name_postfix(src.name)
    constraint = src.constraints.new(type='TRACK_TO')
    constraint.target = dst
    constraint.name = '{}_{:04d}'.format(src_name, num)



def remove_double_path(src, dst, report):
    foam_object = src.parent
    if foam_object is None:
        report({'ERROR'}, 'points object not found')
        return {'CANCELLED'}

    for c in src.constraints:
        if c.target is not None and c.target == dst:
            src.constraints.remove(c)


    for c in dst.constraints:
        if c.target is not None and c.target == src:
            dst.constraints.remove(c)


def create_double_path(src, dst, report):
    foam_object = src.parent
    if foam_object is None:
        report({'ERROR'}, 'points object not found')
        return {'CANCELLED'}

    src_name = remove_blender_name_postfix(src.name)
    dst_name = remove_blender_name_postfix(dst.name)
    
    src_name_set = set()
    dst_name_set = set()
    src_cname = None
    dst_cname = None

    for cur in foam_object.children:
        if cur.type != 'EMPTY':
            continue
        for c in cur.constraints:
            cname = remove_blender_name_postfix(c.name)
            if cname.startswith(src_name+'_'):
                src_name_set.add(cname)
            if cname.startswith(dst_name+'_'):
                dst_name_set.add(cname)

    for i in range(len(src_name_set)+1):
        name = '{}_{:04d}'.format(src_name, i)
        if name not in src_name_set:
            src_cname = name
            break

    for i in range(len(dst_name_set)+1):
        name = '{}_{:04d}'.format(dst_name, i)
        if name not in dst_name_set:
            dst_cname = name
            break

    constraint = src.constraints.new(type='TRACK_TO')
    constraint.target = dst
    constraint.name = src_cname

    constraint = dst.constraints.new(type='TRACK_TO')
    constraint.target = src
    constraint.name = dst_cname


def generate_island_foam(context, root, mesh_root_list, seadogs_tool, report):

    foam_object = get_points_object(root)
    if foam_object is None:
        report({'ERROR'}, 'points object not found')
        return {'CANCELLED'}

    num = 0

    points = []
    for cur in foam_object.children:
        if cur.type != 'EMPTY':
            continue
        cur.name = 'pnt{:04d}'.format(num)
        cur.matrix_world.translation[2] = 0
        cur.constraints.clear()

        num += 1
        points.append(cur)


    mesh_list = []
    for cur in mesh_root_list:
        print('meshes: {}'.format([o.name for o in cur.children if o.type == 'MESH']))
        mesh_list.extend([o for o in cur.children if o.type == 'MESH'])


    bm = bmesh.new()

    for me in mesh_list:
        bm.from_mesh(me.data)

    bvh_tree = BVHTree.FromBMesh(bm, epsilon=0.0001)

    for i in range(len(points)):
        con_num = 0
        for j in range(len(points)): 
            if i == j:
                continue
            source_point = points[i]
            target_point = points[j]
            if check_accessible(source_point, target_point, bvh_tree):
                create_path(source_point, target_point, con_num)
                con_num += 1
    bm.free()




def get_2d_bounds(bm):
    x_min = sys.float_info.max
    x_max = sys.float_info.min
    y_min = sys.float_info.max
    y_max = sys.float_info.min

    for v in bm.verts:
        if x_min > v.co[0]:
            x_min = v.co[0]
        if x_max < v.co[0]:
            x_max = v.co[0]
        if y_min > v.co[1]:
            y_min = v.co[1]
        if y_max < v.co[1]:
            y_max = v.co[1]

    return (x_min, x_max, y_min, y_max)


def generate_island_foam_points(context, root, mesh_root_list, seadogs_tool, report):

    foam_object = get_points_object(root)
    if foam_object is None:
        report({'ERROR'}, 'points object not found')
        return {'CANCELLED'}

    num = len(foam_object.children)

    points = []
    count = seadogs_tool.path_point_count

    mesh_list = []
    for cur in mesh_root_list:
        print('meshes: {}'.format([o.name for o in cur.children if o.type == 'MESH']))
        mesh_list.extend([o for o in cur.children if o.type == 'MESH'])


    bm = bmesh.new()

    for me in mesh_list:
        bm.from_mesh(me.data)

    bvh_tree = BVHTree.FromBMesh(bm, epsilon=0.0001)
    bounds = get_2d_bounds(bm)
    for i in range(count):
        create_random_point(foam_object, bounds, bvh_tree, num+i)
        
        
    bm.free()



class GenerateIslandFoam(bpy.types.Operator):
    bl_idname = "seadogs_util.generate_island_foam"
    bl_label = "Generate island foam"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool
        foam_root = bpy.context.view_layer.objects.active

        selected_objects = [o for o in bpy.context.view_layer.objects.selected if o.name != foam_root.name]
        
        wrong_objects = [o for o in selected_objects if o.type != 'EMPTY' or remove_blender_name_postfix(o.name) != 'root']
        if (len(wrong_objects) > 0) or foam_root.type != 'EMPTY' or remove_blender_name_postfix(foam_root.name) != 'root':
            self.report({'ERROR'}, 'Selected objects should be root')
            return {'CANCELLED'}
            
        

        ret = generate_island_foam(context, foam_root, selected_objects, seadogs_tool, self.report)
        if ret is not None:
            return {'CANCELLED'}

        return {'FINISHED'}


class GenerateIslandFoamPoints(bpy.types.Operator):
    bl_idname = "seadogs_util.generate_island_foam_points"
    bl_label = "Generate island foam"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool
        foam_root = bpy.context.view_layer.objects.active

        selected_objects = [o for o in bpy.context.view_layer.objects.selected if o.name != foam_root.name]
        
        wrong_objects = [o for o in selected_objects if o.type != 'EMPTY' or remove_blender_name_postfix(o.name) != 'root']
        if (len(wrong_objects) > 0) or foam_root.type != 'EMPTY' or remove_blender_name_postfix(foam_root.name) != 'root':
            self.report({'ERROR'}, 'Selected objects should be root')
            return {'CANCELLED'}
            
        

        ret = generate_island_foam_points(context, foam_root, selected_objects, seadogs_tool, self.report)
        if ret is not None:
            return {'CANCELLED'}

        return {'FINISHED'}
    

class AddPath(bpy.types.Operator):
    bl_idname = "seadogs_util.add_path"
    bl_label = "Add path"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (len(context.view_layer.objects.selected) == 2 
                and context.view_layer.objects.selected[0].parent == context.view_layer.objects.selected[1].parent 
                and context.view_layer.objects.selected[0].type == 'EMPTY'
                and context.view_layer.objects.selected[1].type == 'EMPTY' 
                and context.view_layer.objects.selected[0].parent is not None)

    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool

        if len(context.view_layer.objects.selected) != 2:
            self.report({'ERROR'}, 'Two locators should be selected')
            return {'CANCELLED'}
        


        ret = create_double_path(context.view_layer.objects.selected[0], context.view_layer.objects.selected[1], self.report)
        if ret is not None:
            return {'CANCELLED'}

        return {'FINISHED'}
    
class RemovePath(bpy.types.Operator):
    bl_idname = "seadogs_util.remove_path"
    bl_label = "Remove path"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (len(context.view_layer.objects.selected) == 2 
                and context.view_layer.objects.selected[0].parent == context.view_layer.objects.selected[1].parent 
                and context.view_layer.objects.selected[0].type == 'EMPTY'
                and context.view_layer.objects.selected[1].type == 'EMPTY' 
                and context.view_layer.objects.selected[0].parent is not None)

    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool

        if len(context.view_layer.objects.selected) != 2:
            self.report({'ERROR'}, 'Two locators should be selected')
            return {'CANCELLED'}
        


        ret = remove_double_path(context.view_layer.objects.selected[0], context.view_layer.objects.selected[1], self.report)
        if ret is not None:
            return {'CANCELLED'}

        return {'FINISHED'}

class MinMaxCollector:
    def __init__(self):
        self.x_min = sys.float_info.max
        self.x_max = sys.float_info.min
        self.y_min = sys.float_info.max
        self.y_max = sys.float_info.min
        self.z_min = sys.float_info.max
        self.z_max = sys.float_info.min

    def add_vertex(self, v):
        if self.x_min > v.co[0]:
            self.x_min = v.co[0]
        if self.x_max < v.co[0]:
            self.x_max = v.co[0]
        if self.y_min > v.co[1]:
            self.y_min = v.co[1]
        if self.y_max < v.co[1]:
            self.y_max = v.co[1]
        if self.z_min > v.co[2]:
            self.z_min = v.co[2]
        if self.z_max < v.co[2]:
            self.z_max = v.co[2]


    def get_min(self):
        return Vector((self.x_min, self.y_min, self.z_min))
    
    def get_sizes(self):
        return (self.x_max - self.x_min, self.y_max - self.y_min, self.z_max - self.z_min)



def consolidate_vertexes_from_buckets_with_ver(ver1, buckets, delta, counts, x, y, z):

    moved = 0
    x_s = x - 1 if x > 1 else x
    x_f = x + 2 if x < counts[0] - 1 else x + 1

    y_s = y - 1 if y > 1 else y
    y_f = y + 2 if y < counts[1] - 1 else y + 1

    z_s = z - 1 if z > 1 else z
    z_f = z + 2 if z < counts[2] - 1 else z + 1

    for i in range(x_s, x_f):
        for j in range(y_s, y_f):
            for k in range(z_s, z_f):
                if buckets[get_coord(i, j, k, counts)] is None:
                    continue
                for n in range(len(buckets[get_coord(i, j, k, counts)])):
                    ver2 = buckets[get_coord(i, j, k, counts)][n]
                    if (ver2.co-ver1.co).length <= delta and ver2.co != ver1.co:
                        ver2.co = ver1.co
                        moved += 1


    return moved


def consolidate_vertexes_from_buckets(buckets, delta, counts):
    total_moved = 0
    for i in range(counts[0]):
        print('i = {}/{}'.format(i, counts[0]))
        for j in range(counts[1]):
            for k in range(counts[2]):
                if buckets[get_coord(i, j, k, counts)] is None:
                    continue
                while True:
                    moved = 0
                    for n in range(len(buckets[get_coord(i, j, k, counts)])):
                        ver = buckets[get_coord(i, j, k, counts)][n]
                        moved += consolidate_vertexes_from_buckets_with_ver(ver, buckets, delta, counts, i, j, k)
                    if moved == 0:
                        break
                    else:
                       print('bucket[{}][{}][{}] moved {}'.format(i, j, k, moved)) 
                       total_moved += moved
    print('consolidating finised. moved {} verts'.format(total_moved)) 


def get_coord(i, j, k, sizes):
    return i*sizes[1]*sizes[2] + j*sizes[2] + k

def consolidate_vertexes(context, mesh_list, seadogs_tool, report):

    delta = seadogs_tool.consolidate_delta
    bucket_size = seadogs_tool.bucket_size

    if len(mesh_list) == 0:
        report({'WARNING'}, 'No meshes selected')
        return None
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    for cur in mesh_list:
        cur.select_set(True)
    bpy.context.view_layer.objects.active = mesh_list[0]

    bpy.ops.object.mode_set(mode='EDIT')


    bms = [bmesh.from_edit_mesh(obj.data) for obj in mesh_list]

    bounds = MinMaxCollector()
    for cur in bms:
        for v in cur.verts:
            bounds.add_vertex(v)
   
    counts = [int(dim / bucket_size) + 1 for dim in bounds.get_sizes()]


    total_count = counts[0] * counts[1] * counts[2]


    print('size={} buckets={}'.format(bounds.get_sizes(), counts))
    print('allocating buckets...')
    buckets = [None]*total_count
    #for i in range(counts[0]):
    #    print('i = {}/{}'.format(i, counts[0]))
    #    buckets[i] = [None]*counts[1]
    #    for j in range(counts[1]):
    #        buckets[i][j] = [None]*counts[2]
    print('done')

    print('placing vertexes...')
    for i in range(len(bms)):
        cur = bms[i]
        print('mesh {}/{}'.format(i, len(bms)))
        for v in cur.verts:
            x_bucket = int(v.co[0] / bucket_size)
            y_bucket = int(v.co[1] / bucket_size)
            z_bucket = int(v.co[2] / bucket_size)

            if buckets[get_coord(x_bucket, y_bucket, z_bucket, counts)] is None:
                buckets[get_coord(x_bucket, y_bucket, z_bucket, counts)] = []
            buckets[get_coord(x_bucket, y_bucket, z_bucket, counts)].append(v)

    print('done')

    print('consolidating...')
    consolidate_vertexes_from_buckets(buckets, delta, counts)
    print('done')

    for i in range(len(bms)):
        bmesh.update_edit_mesh(mesh_list[i].data, loop_triangles=False, destructive=False)


def remove_void_faces(context, mesh_list, seadogs_tool, report):

    if len(mesh_list) == 0:
        report({'WARNING'}, 'No meshes selected')
        return None
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    for cur in mesh_list:
        cur.select_set(True)
    bpy.context.view_layer.objects.active = mesh_list[0]

    bpy.ops.object.mode_set(mode='EDIT')


    bms = [bmesh.from_edit_mesh(obj.data) for obj in mesh_list]

    count = 0
    for cur in bms:
        for f in cur.faces:
            if f.calc_area() == 0 or f.calc_perimeter() == 0:
                f.select_set(True)
                count += 1
    bpy.ops.mesh.split()
    bpy.ops.mesh.delete(type='VERT')

    print('deleted zero-size faces count {}'.format(count))


    for i in range(len(bms)):
        bmesh.update_edit_mesh(mesh_list[i].data)

    bms = [bmesh.from_edit_mesh(obj.data) for obj in mesh_list]

    empty_objects = []
    for i in range(len(bms)):
        if len(bms[i].verts) == 0:
            empty_objects.append(i)

    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')

    count = 0
    for i in empty_objects:
        mesh_list[i].select_set(True)
        count += 1

    bpy.ops.object.delete(use_global=False, confirm=False)

    print('deleted empty object {}'.format(count))

    

def detach_meshes(meshes_map):
    bpy.ops.object.mode_set(mode='OBJECT')
    for k, v in meshes_map.items():
        bpy.ops.object.select_all(action='DESELECT')
        for m in v:
            m.select_set(True)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def attach_meshes(meshes_map):
    bpy.ops.object.mode_set(mode='OBJECT')
    
    for k, v in meshes_map.items():
        bpy.ops.object.select_all(action='DESELECT')
        for m in v:
            m.select_set(True)
        
        bpy.context.view_layer.objects.active = bpy.data.objects[k]
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)


class ConsolidateVertexes(bpy.types.Operator):
    bl_idname = "seadogs_util.consolidate_vertexes"
    bl_label = "Consolidate vertexes"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool

        selected_objects = [o for o in bpy.context.view_layer.objects.selected]
        
        wrong_objects = [o for o in selected_objects if o.type != 'EMPTY' or remove_blender_name_postfix(o.name) != 'root']
        if len(wrong_objects) > 0:
            self.report({'ERROR'}, 'Selected objects should be root')
            return {'CANCELLED'}
            
        mesh_list = []
        root_map = {}
        for cur in selected_objects:
            print('meshes: {}'.format([o.name for o in cur.children if o.type == 'MESH']))
            meshes = [o for o in cur.children if o.type == 'MESH']
            root_map[cur.name] = meshes
            mesh_list.extend(meshes)


        detach_meshes(root_map)
        ret = consolidate_vertexes(context, mesh_list, seadogs_tool, self.report)
        attach_meshes(root_map)
        if ret is not None:
            return {'CANCELLED'}


        return {'FINISHED'}
    
class ConsolidateVertexesForMeshes(bpy.types.Operator):
    bl_idname = "seadogs_util.consolidate_vertexes_for_meshes"
    bl_label = "Consolidate vertexes for mesh"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool

        selected_objects = [o for o in bpy.context.view_layer.objects.selected]
        
        wrong_objects = [o for o in selected_objects if o.type != 'MESH']
        if len(wrong_objects) > 0:
            self.report({'ERROR'}, 'Selected objects should be a mesh')
            return {'CANCELLED'}

        ret = consolidate_vertexes(context, selected_objects, seadogs_tool, self.report)
        if ret is not None:
            return {'CANCELLED'}

        return {'FINISHED'}


class DeleteEmpty(bpy.types.Operator):
    bl_idname = "seadogs_util.delete_empty"
    bl_label = "Delete empty"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        seadogs_tool = context.scene.seadogs_tool

        selected_objects = [o for o in bpy.context.view_layer.objects.selected]
        
        wrong_objects = [o for o in selected_objects if o.type != 'EMPTY' or remove_blender_name_postfix(o.name) != 'root']
        if len(wrong_objects) > 0:
            self.report({'ERROR'}, 'Selected objects should be root')
            return {'CANCELLED'}
            
        mesh_list = []
        for cur in selected_objects:
            print('meshes: {}'.format([o.name for o in cur.children if o.type == 'MESH']))
            meshes = [o for o in cur.children if o.type == 'MESH']
            mesh_list.extend(meshes)

        ret = remove_void_faces(context, mesh_list, seadogs_tool, self.report)
        if ret is not None:
            return {'CANCELLED'}

        return {'FINISHED'}

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
    foam_inverted : BoolProperty(
        name="Inverted foam",
        description="Foam direction: 'inverted' -- to island, otherwise -- from island.",
        default = False
        )
    foam_depth : FloatProperty(
        name = "Foam depth",
        description="Foam depth",
        default = 60.0,
        min = 10.0,
        max = 100.0 
        )
    
    path_point_count : IntProperty(
        name = "Path point count",
        description="Path point count",
        default = 45,
        min = 1,
        max = 500 
        )
    
    path_point_max_range : FloatProperty(
        name = "Path point max range",
        description="Path point max range",
        default = 500.0,
        min = 100.0,
        max = 2000.0 
        )
    
    consolidate_delta : FloatProperty(
        name = "Delta",
        description="Delta",
        default = 0.001,
        )

    bucket_size : FloatProperty(
        name = "Bucket size",
        description="Bucket size",
        default = 0.01,
        )



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
        seadogs_tool = context.scene.seadogs_tool

        row = layout.row()
        row.label(text = "Foam utils")
        row = layout.row()
        row.prop(seadogs_tool, "foam_inverted", text="Inverted foam")
        row = layout.row()
        row.prop(seadogs_tool, "foam_depth", text="Foam depth")

        row = layout.row()
        row.label(text = "Generate foam")
        row = layout.row()
        colL = row.column(align=False)
        colR = row.column(align=False)
        colL.operator("seadogs_util.generate_foam_near", text='near')
        colR.operator("seadogs_util.generate_foam_far", text='near')
        colR.operator("seadogs_util.generate_foam_farthest", text='farthest')

        layout.row().separator()

        row = layout.row()
        row.label(text = "Island foam util")
        row = layout.row()
        row.prop(seadogs_tool, "path_point_count", text="Path point count")
        row = layout.row()
        row.prop(seadogs_tool, "path_point_max_range", text="Path point max range")
        row = layout.row()
        colL = row.column(align=False)
        colR = row.column(align=False)
        colL.operator("seadogs_util.generate_island_foam_points", text='Generate points')
        colL.operator(AddPath.bl_idname, text='Add path')

        colR.operator("seadogs_util.generate_island_foam", text='Generate pathes')
        colR.operator(RemovePath.bl_idname, text='Remove path')

        layout.row().separator()
        row = layout.row()
        row.label(text = "Consolidate vertexes util")
        row = layout.row()
        row.prop(seadogs_tool, "consolidate_delta", text="Delta")
        row = layout.row()
        row.prop(seadogs_tool, "bucket_size", text="Bucket size")
        row = layout.row()
        row.operator(ConsolidateVertexes.bl_idname, text='Consolidate')
        row = layout.row()
        row.operator(ConsolidateVertexesForMeshes.bl_idname, text='Consolidate for mesh')
        row = layout.row()
        row.operator(DeleteEmpty.bl_idname, text='Delete empty')

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
    GenerateFoam('farthest'),
    FixLocators('man'),
    FixLocators('danny'),
    GenerateIslandFoam,
    GenerateIslandFoamPoints,
    AddPath,
    RemovePath,
    ConsolidateVertexes,
    ConsolidateVertexesForMeshes,
    DeleteEmpty
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