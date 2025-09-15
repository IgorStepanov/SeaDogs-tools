import os
import bpy, bmesh
import sys
import re
import fnmatch
import math
from math import cos, sin, radians
from mathutils import Vector, kdtree
import functools
from pathlib import Path

from bpy.props import StringProperty, BoolProperty, PointerProperty, IntProperty
from bpy.types import PropertyGroup, Panel, Scene, Operator
from bpy.utils import register_class, unregister_class
from import_gm import import_gm

bl_info = {
    "name" : "SeaDogs GM Ship Assemble",
    "author" : "Tosyk",
    "version" : (1, 1),
    "blender" : (4, 4, 1),
    "location" : "View3d > Tool",
    "warning" : "",
    "wiki_url" : "",
    "category" : "Import",
}


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):

    clear_scn_bool : BoolProperty(
        name="Clear Scene before import new",
        description="Clear Scene before import new",
        default = True
        )

    sail_tex_def_str : StringProperty(
        name="Sail texture",
        description="Type default sail texture name (parus_common.tga).\nScript will look for it inside specified Texture folder",
        default="parus_common.tga"
        )

    flag_tex_def_str : StringProperty(
        name="Flag texture",
        description="Type default flag texture name (parus_common.tga).\nScript will look for it inside specified Texture folder",
        default="flagall.tga"
        )

    rope_tex_def_str : StringProperty(
        name="Rope texture",
        description="Type default rope texture name (rope.tga).\nScript will look for it inside specified Texture folder.\nSould be vertical texture",
        default="rope.tga"
        )

    rope_type_int : IntProperty(
        name = "Set rope type",
        description="Set rope type.\nType 1: vertical texture.\nType 2: horizontal texture",
        default = 1,
        min = 1,
        max = 2
        )

    flag_type_int : IntProperty(
        name = "Set flag type",
        description="Set flag type.\nType 1: old flag texture, low quality.\nType 2: new flag texture, high quality",
        default = 1,
        min = 1,
        max = 2
        )

    flag_num_int : IntProperty(
        name = "Set flag number",
        description="Set flag number.\nChoose number of flag from texture",
        default = 1,
        min = 1,
        max = 10
        )

    imp_ship_bool : BoolProperty(
        name="Import ship geometry",
        description="Import ship geometry",
        default = True
        )

    gen_vants_bool : BoolProperty(
        name="Generate vant(s) by given empties coordinates.",
        description="Generate vant(s) by given empties coordinates.",
        default = False
        )

    gen_rig_bool : BoolProperty(
        name="Generate rig ropes by given empties coordinates.",
        description="Generate rig ropes by given empties coordinates.",
        default = False
        )

    gen_sails_bool : BoolProperty(
        name="Generate sail plains by given empties coordinates.",
        description="Generate sail plains by given empties coordinates.",
        default = False
        )

    gen_flag_bool : BoolProperty(
        name="Generate sail plains by given empties coordinates.",
        description="Generate sail plains by given empties coordinates.",
        default = False
        )

    gen_penn_bool : BoolProperty(
        name="Generate sail plains by given empties coordinates.",
        description="Generate sail plains by given empties coordinates.",
        default = False
        )

    cloth_sail_bool : BoolProperty(
        name="Apply cloth modifier to sail plains.",
        description="Apply cloth modifier to sail plains.",
        default = False
        )

    anim_sail_bool : BoolProperty(
        name="Animate sail plains with Wind force.",
        description="Animate sail plains with Wind force.",
        default = False
        )

    ship_path : StringProperty(
        name = "",
        description="Choose a Ships directory:",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
        )

    texs_path : StringProperty(
        name = "",
        description="Choose a Texture directory:",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
        )

    hull_num_int : IntProperty(
        name = "Set Hull Number",
        description="Set Hull Number.\nYou can specify the number or not - script will handle anything",
        default = 1,
        min = 1,
        max = 64
        )

    sail_quality_int : IntProperty(
        name = "Set sail/flag subdivision",
        description="Set sail/flag subdivision (8 - optimal)",
        default = 4,
        min = 0,
        max = 10
        )



def find_principled_node(mtl):
    principled_node = None
    for node in mtl.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    return principled_node

def find_specular_input(bsdf):
    specular_input = None
    for i, o in enumerate(bsdf.inputs):
        if o.name == 'Specular IOR Level':
            specular_input = o
    return specular_input

def remove_blender_name_postfix(name):
    return re.sub(r'\.\d{3}', '', name)

def get_root_for_collection(coll):

    root_objects = [o for o in coll.objects if o.parent is None]

    if len(root_objects) != 1:
        raise TypeError('Wrong collenction "{}". Expect 1 child, found: {}'.format(coll.name, len(root_objects)))
    return root_objects[0]

# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class ImpSEShip_Button(Operator):
    bl_label = "Process setings"
    bl_idname = "impseship.main"
    
    def execute(self, context):
        #c = bpy.context
        #ob = bpy.ops.object
        #objects = bpy.data.objects
        #scene = c.scene
        
        mytool = bpy.context.scene.my_tool

        import_and_assemble_ship(context)
        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class MAIN_PT_ImpSEShip:
    #bl_label = "Import & Assemble Ship"
    #bl_idname = "MAIN_PT_ImpSEShip"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Import GM Ship"
    #bl_context = "objectmode" 
    #bl_options = {'HIDE_HEADER'}


class SETUP_PT_ImpSEShip(MAIN_PT_ImpSEShip, Panel):
    bl_label = "Import & Assemble Ship"
    bl_idname = "SETUP_PT_ImpSEShip"
    bl_icon = {'TOOL_SETTINGS'}

    def draw_header(self, context):
        # Example property to display a checkbox, can be anything
        self.layout.label(text="", icon="MOD_OCEAN")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        row = layout.row()
        layout.prop(mytool, "clear_scn_bool", text="Clear Scene First")

        row = layout.row()
        row.label(text = "Path and texture settings:", icon = 'TOOL_SETTINGS')

        # display the properties
        col = layout.column(align=True)
        col.label(text = "Ship folder:")
        col.prop(mytool, "ship_path", text="")
        layout.row().separator()

        box = layout.box()
        row = box.row()
        colT = row.column(align=False)
        colT.label(text = "Texture folder:")
        colT.prop(mytool, "texs_path", text="")
        colT.label(text = "Sail texture name:")
        colT.prop(mytool, "sail_tex_def_str", text="")
        colT.label(text = "Rope texture name:")
        colT.prop(mytool, "rope_tex_def_str", text="")
        colT.prop(mytool, "rope_type_int", text="Rope Texture Vertical/Horizontal")

        colT.label(text = "Flag texture name:")
        colT.prop(mytool, "flag_tex_def_str", text="")
        colT.prop(mytool, "flag_type_int", text="Flag Texture Type")
        colT.prop(mytool, "flag_num_int", text="Flag Number on a Texture")
        colT.prop(mytool, "hull_num_int", text="Ship Hull Texture Number")
        
        layout.row().separator()
        row = layout.row()
        row.label(text = "Main settings:", icon = 'MOD_TINT')
        
        layout.prop(mytool, "imp_ship_bool", text="Import Ship (*.gm files)")
        
        box1 = layout.box()
        row1 = box1.row()
        colM = row1.column(align=False)
        colM.prop(mytool, "gen_rig_bool", text="Generate Rig (blender math)")
#        colM.prop(mytool, "gen_vants_bool", text="Generate Vants (blender math)")
        colM.prop(mytool, "gen_sails_bool", text="Generate Sails (blender math)")
        colM.prop(mytool, "gen_flag_bool", text="Generate Flags (blender math)")
        colM.prop(mytool, "gen_penn_bool", text="Generate Pennants (blender math)")
        colM.prop(mytool, "sail_quality_int", text="Sail/Flag Cloth Subdivision")
        colM.prop(mytool, "cloth_sail_bool", text="Clothing Sails (Cloth modifier)")
        colM.prop(mytool, "anim_sail_bool", text="Animate Sails (Blender physics)")
        #layout.prop(mytool, "my_float", text="Float Property")



        row = layout.row()
        row.scale_y = 2.0
        row.operator("impseship.main")


# -----------------------------------------------------------
# Set variables
# -----------------------------------------------------------
"""
c = bpy.context
ob = bpy.ops.object
objects = bpy.data.objects
scene = c.scene
curves = bpy.data.curves
"""


# -----------------------------------------------------------
# Settings
# -----------------------------------------------------------
#import_ship = 'false'      # import ship basic geometry or not
#generate_rig = 'false'     # generate rig and ropes or not
#sail_quality = 0          # sail object quality, subdivision value
#gen_sails_bool = 'false'    # should sail objects to be created or not
#cloth_sail_bool = 'false'     # should cloth modifier to be added to the sail objects or not
#anim_sail_bool = 'false'   # should sail objects to be animated or not
wind_dir = 'l'            # wind direction (left(l), right(r) or center(c))


# ===========================================================
# Function: remove all from scene
# ===========================================================
def clear_scene():
    for c in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.unlink(c)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for c in bpy.data.collections:
        if not c.users:
            bpy.data.collections.remove(c)

    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()


# ===========================================================
# Function: remove redundant collection
# ===========================================================
def rem_default_coll():
    name = "Collection"
    remove_collection_objects = True

    #coll = c.collection # 
    coll = bpy.data.collections.get(name)

    if coll:
        if remove_collection_objects:
            obs = [o for o in coll.objects if o.users == 1]
            while obs:
                bpy.data.objects.remove(obs.pop())

        bpy.data.collections.remove(coll)


# ===========================================================
# Function: create tube curve for the rope
# ===========================================================
def make_tubes(context, obj, rig_obj_name, ship_name, length, bevel_depth=1.026, resolution=1):

    my_tool = context.scene.my_tool
    mesh = obj.data
    curves = bpy.data.curves
    curve_name = rig_obj_name
    rope_type_int = my_tool.rope_type_int
    hull_num_int = my_tool.hull_num_int

    rope_tex_def_str = my_tool.rope_tex_def_str
    texs_path = my_tool.texs_path


    # -----------------------------------------------------------
    # Create new cylinder
    # -----------------------------------------------------------
    # if exists, pick up else generate a new one
    cu = curves.get(curve_name + '_mesh', curves.new(name=curve_name, type='CURVE'))
    cu.dimensions = '3D'
    cu.fill_mode = 'FULL'
    cu.bevel_depth = bevel_depth
    cu.bevel_resolution = resolution
    cu_obj = bpy.data.objects.get(curve_name, bpy.data.objects.new(curve_name, cu))

    # break down existing splines entirely.
    if cu.splines:
        cu.splines.clear()

    # and rebuild
    verts = mesh.vertices
    for e in mesh.edges:
        idx_v1, idx_v2 = e.vertices
        v0, v1 = verts[idx_v1].co, verts[idx_v2].co
        full_flat = [v0[0], v0[1], v0[2], 0.0, v1[0], v1[1], v1[2], 0.0]

        # each spline has a default first coordinate but we need two.
        segment = cu.splines.new('POLY')
        segment.points.add(1)
        segment.points.foreach_set('co', full_flat)

    if not curve_name in bpy.context.scene.objects:
        bpy.context.collection.objects.link(cu_obj)


    # -----------------------------------------------------------
    # Edit new cylinder UVs
    # -----------------------------------------------------------
    root_ob = bpy.context.scene.objects[curve_name] # Get the object
    bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
    bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
    root_ob.select_set(True)

    bpy.ops.object.convert(target='MESH')
    
    o_uv = bpy.data.objects[curve_name]
    for uvmap in o_uv.data.uv_layers : uvmap.name = 'UVMap'
    uvMap = o_uv.data.uv_layers['UVMap']
    
    # Rotate UV
    rad = (radians(-90)) if rope_type_int == 1 else (radians(0))
    anchor = (0.5, 0.5)
    rot = make_rotation_transformation(rad, anchor)
    for v in o_uv.data.loops :
        uvMap.data[v.index].uv = rot(uvMap.data[v.index].uv )

    # Scale UV
    pivot = Vector( (0, 0) )
    scale = Vector( (1, 1*length) ) if rope_type_int == 1 else (Vector( (1*length*2, 1) ))
    ScaleUV( uvMap, scale, pivot )


    # -----------------------------------------------------------
    # Create material
    # -----------------------------------------------------------
    # Look for sail and flag textures if not found create default
    texture_path_found = None

    if rope_tex_def_str is not None:

        # Set texture
        mat_name = ship_name + '_Rope_Defaul_Mat'
        texture_file = rope_tex_def_str

        for ship_dir in Path(texs_path).rglob(f'**/{ship_name}'):
            for hull_dir in ([f'hull{hull_num_int}',] if hull_num_int is not None else []) + ['hull1']:
                if (ship_dir/hull_dir).exists() and (ship_dir/hull_dir/texture_file).exists():
                    texture_path_found = ship_dir/hull_dir/texture_file
                    break
            if texture_path_found is not None:
                break

        if texture_path_found is None:
            for ship_dir in Path(texs_path).rglob(f'**/{ship_name}'):
                for tex_file in ship_dir.rglob(f'**/{texture_file}'):
                    texture_path_found = tex_file
                    break
                if texture_path_found is not None:
                    break

        if texture_path_found is None:
            for ship_dir in Path(texs_path).rglob(f'**/{texture_file}'):
                texture_path_found = ship_dir
                break

    texture_path_found = texture_path_found or os.path.join(texs_path, texture_file)

    texture_path = str(texture_path_found)
    print(curve_name, 'use this texture:', texture_path)


    ac_ob = bpy.context.active_object

    # Get material
    mat = bpy.data.materials.get(mat_name)

    if mat is None:
        # create material
        mat = bpy.data.materials.new(name = mat_name)
        mat.use_nodes = True
        mat.blend_method = 'CLIP'

        bsdf = find_principled_node(mat)
        if bsdf is None:
            raise TypeError("No Principled BSDF node found in the material")

        spec = find_specular_input(bsdf)
        if spec is None:
            raise TypeError("No Specular IOR Level input found in the material.")

        spec.default_value = 0.0
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')

        if texture_file in bpy.data.images:
            texImage.image = bpy.data.images[texture_file]
        else:
            if os.path.isfile(texture_path):
                texImage.image = bpy.data.images.load(texture_path)
            else:
                placeholder_image = bpy.data.images.new(texture_file, width=1, height=1)
                placeholder_image.pixels = [0.5,0.5,0.5,1]
                texImage.image = placeholder_image

        mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
        mat.node_tree.links.new(bsdf.inputs['Alpha'], texImage.outputs['Alpha'])


    # Assign it to object
    if ac_ob.data.materials:
        # assign to 1st material slot
        ac_ob.data.materials[0] = mat
    else:
        # no slots
        ac_ob.data.materials.append(mat)



def found_new_collection(coll_set, name_pattern):
    result = None
    for c in bpy.data.collections:
        if c.name not in coll_set and remove_blender_name_postfix(c.name) == name_pattern:
            result = c
            break
    return result

# ===========================================================
# Function: import ship parts from gm files
# ===========================================================



def is_locator_match(obj, name):
    return obj.type == 'EMPTY' and remove_blender_name_postfix(obj.name).lower() == name.lower()

def find_the_same_name_objects(loc_name, obj_name):
    return [o for o in bpy.context.scene.objects if o.name != loc_name and remove_blender_name_postfix(o.name).lower() == obj_name.lower()]


def import_objects(obj_name, file, ship_name, my_tool):
    
    hull_num_int = my_tool.hull_num_int
    texs_path = my_tool.texs_path
    ship_path = my_tool.ship_path
    d = ship_path
    file_name = ship_name + '_' + obj_name

    coll_set = set()
    for c in bpy.data.collections:
        coll_set.add(c.name)

    for o in bpy.context.scene.objects:
        if is_locator_match(o, obj_name):
            print(obj_name, 'object found')
            locator_name = o.name
            #import_gm(bpy.context, hull_num_int, file_path = file, textures_path = texs_path, report_func = report)
            getattr(bpy.ops, 'import').gm(filepath = file, textures_path = texs_path, hull_num_int = hull_num_int)

            coll_source = found_new_collection(coll_set, file_name)
            print('coll_source name: "{}"'.format(coll_source.name))
            
            root_source = get_root_for_collection(coll_source)
            root_name = root_source.name

            print('root name: "{}"'.format(root_name))
            # -----------------------------------------------------------
            # Set selected objects from imported objects to a proper
            # collection
            # -----------------------------------------------------------

            # Set target collection to a known collection 
            coll_target = bpy.context.scene.collection.children.get(ship_name)

            #select root and then its childrens
            root_ob = bpy.context.scene.objects[root_name] # Get the object
            bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
            bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
            root_ob.select_set(True)

            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')

            # List of object references
            objs = bpy.context.selected_objects

            # If target found and object list not empty
            if coll_target and objs:

                # Loop through all objects
                for o in objs:
                    # Loop through all collections the obj is linked to
                    for coll in o.users_collection:
                        # Unlink the object
                        coll.objects.unlink(o)

                    # Link each object to the target collection
                    coll_target.objects.link(o)


            # -----------------------------------------------------------
            # Reposition imported object to a proper dummy
            # -----------------------------------------------------------
            target = bpy.data.objects[locator_name]
            source = bpy.data.objects[root_name]
            source.location += target.matrix_world.translation - source.matrix_world.translation


            # -----------------------------------------------------------
            # Reparent imported object to a proper dummy
            # -----------------------------------------------------------
            parn = bpy.data.objects[locator_name]
            chld = bpy.data.objects[root_name].children
            bpy.ops.object.select_all(action='DESELECT')
            for c in chld:
                c.select_set(True)
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            bpy.ops.object.select_all(action='DESELECT')
            for c in chld:
                c.select_set(True)
            parn.select_set(True)
            bpy.context.view_layer.objects.active = parn
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
            bpy.ops.object.select_all(action='DESELECT')

            # -----------------------------------------------------------
            # Remove redundant collection
            # -----------------------------------------------------------

            #deselect all
            bpy.ops.object.select_all(action='DESELECT')

            # Remove collection hierarchy
            collection = bpy.data.collections.get(file_name)
             
            for obj in collection.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
                
            bpy.data.collections.remove(collection)


            # -----------------------------------------------------------
            # Rename internal dummy with same name to '*_rope'
            # -----------------------------------------------------------

            # Deselect all
            bpy.ops.object.select_all(action='DESELECT')

            # Rename object
            rope_objects = find_the_same_name_objects(locator_name, obj_name)

            if len(rope_objects):
                for obj in rope_objects:
                    if obj.type == 'EMPTY':
                        obj.name = obj_name + '_ropes'

            bpy.context.view_layer.update()
            return True

    print('-------------------------------------------------------------------')
    print('')
    return False


def creating_rope(context, line_start, line_end, rope_num, rig_type, rig_dummy_name, ship_name, rig_obj_name):
    # -----------------------------------------------------------
    # Creating line between 2 points
    # -----------------------------------------------------------

    # Reference two cylinder objects
    c1 = bpy.data.objects[line_start]
    c2 = bpy.data.objects[line_end]


    # Create new connector mesh and mesh object and link to scene
    if rig_type == 'rope':
        rig_obj_name = 'rope_' + rope_num
        rope_width = 0.026
    elif rig_type == 'fal':
        rig_obj_name = 'fal_' + rope_num
        rope_width = 0.026
    elif rig_type == 'v_rope':
        rope_width = 0.02
    elif rig_type == 'stave':
        rope_width = 0.02

    
    # Calculate distance between 2 points to use for proper UV
    length = math.dist(c1.matrix_world.translation, c2.matrix_world.translation)
    #print(rig_obj_name, 'length:', length)

    #print('Rope final name:', rig_obj_name)
    #rig_obj_name_temp = 'EdgesObject'

    m = bpy.data.meshes.new(rig_obj_name)

    bm = bmesh.new()
    v1 = bm.verts.new( c1.matrix_world.translation )
    v2 = bm.verts.new( c2.matrix_world.translation )
    e  = bm.edges.new([v1,v2])

    bm.to_mesh(m)

    o = bpy.data.objects.new( rig_obj_name, m )
    bpy.context.scene.collection.objects.link( o )

    # Hook connector vertices to respective cylinders
    for i, cyl in enumerate([ c1, c2 ]):
        bpy.ops.object.select_all( action = 'DESELECT' )
        cyl.select_set(True)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o # Set connector as active

        # Select vertex
        bpy.ops.object.mode_set(mode='OBJECT')
        o.data.vertices[i].select = True    
        bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.object.hook_add_selob() # Hook to cylinder

        bpy.ops.object.mode_set(mode='OBJECT')
        o.data.vertices[i].select = False 


    # -----------------------------------------------------------
    # Add modifiers to the rope V1
    # -----------------------------------------------------------
    """
    m = o.modifiers.new('Skin', 'SKIN')
    for v in o.data.skin_vertices[0].data:
        rad = 0.03
        v.radius = rad, rad

    # Make shading smooth
    m.use_smooth_shade = True

    # Add details to the rope, make it not rectangular
    m = o.modifiers.new('Subsurf', 'SUBSURF' )
    m.levels = 1
    m.render_levels = 1

    # Add simplifier modifier
    m = o.modifiers.new('Decimate', 'DECIMATE' )
    m.decimate_type = 'DISSOLVE'
    m.angle_limit = 0.48 # arround 28 degree

    bpy.ops.object.select_all( action = 'DESELECT' )
    """


    # -----------------------------------------------------------
    # Add modifiers to the rope V2
    # -----------------------------------------------------------
    b = bpy.data.objects[rig_obj_name]
    b.name = rig_obj_name + '_temp'
    make_tubes(context, b, rig_obj_name, ship_name, length, rope_width, 1)
    bpy.data.objects.remove(b, do_unlink=True)


    # -----------------------------------------------------------
    # Parent rope to 'rig' dummy
    # -----------------------------------------------------------
    a = bpy.data.objects[rig_dummy_name]
    b = bpy.data.objects[rig_obj_name]
    b.parent = a


    # -----------------------------------------------------------
    # Add rope to ship collection
    # -----------------------------------------------------------

    # Set target collection to a known collection 
    coll_target = bpy.context.scene.collection.children.get(ship_name)

    # Select rope
    root_ob = bpy.context.scene.objects[rig_obj_name] # Get the object
    bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
    bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
    root_ob.select_set(True)

    # List of object references
    objs = bpy.context.selected_objects

    # If target found and object list not empty
    if coll_target and objs:

        # Loop through all objects
        for o in objs:
            # Loop through all collections the obj is linked to
            for coll in o.users_collection:
                # Unlink the object
                coll.objects.unlink(o)

            # Link each object to the target collection
            coll_target.objects.link(o)

    bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
    bpy.context.view_layer.update()

    """
    # -----------------------------------------------------------
    # Apply all modifiers
    # -----------------------------------------------------------

    #obj = bpy.data.objects['connector']
    #obj.modifiers.remove(obj.modifiers.get('Skin.001'))

    # pick any object
    obj = bpy.data.objects['connector']

    # set the object to active_object
    c.view_layer.objects.active = obj

    target_obj = c.active_object
    for modifier in target_obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    """
    

# ===========================================================
# Function: stop playback animation
# ===========================================================
def stop_playback(scene):
    if bpy.context.scene.frame_current == 30:
        bpy.ops.screen.animation_cancel(restore_frame=False)


# ===========================================================
# Function: select vertices between 2 points
# ===========================================================
def get_verts_in_line(v1, v2, sailMsh):
    threshold = 0.001
    vec = (v2.co - v1.co).normalized()
    return [v.index for v in sailMsh.vertices if ((v.co-v1.co).normalized()-vec).length < threshold]


# ===========================================================
# Function: apply all modifiers
# ===========================================================
def apply_m(sail_o):

    # pick any object
    obj = bpy.data.objects[sail_o]

    # set the object to active_object
    bpy.context.view_layer.objects.active = obj

    target_obj = bpy.context.active_object
    for modifier in target_obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)


    # Remove wind
    wind_obj = get_wind_object()
    if wind_obj is not None:
        bpy.ops.object.select_all(action='DESELECT')
        wind_obj.select_set(True)
        bpy.ops.object.delete()



#Scale a 2D vector v, considering a scale s and a pivot point p
def Scale2D( v, s, p ):
    return ( p[0] + s[0]*(v[0] - p[0]), p[1] + s[1]*(v[1] - p[1]) )     


#Scale a UV map iterating over its coordinates to a given scale and with a pivot point
def ScaleUV( uvMap, scale, pivot ):
    for uvIndex in range( len(uvMap.data) ):
        uvMap.data[uvIndex].uv = Scale2D( uvMap.data[uvIndex].uv, scale, pivot )

 
def make_rotation_transformation(angle, origin=(0, 0)):
    cos_theta, sin_theta = cos(angle), sin(angle)
    x0, y0 = origin    
    def xform(point):
        x, y = point[0] - x0, point[1] - y0
        return (x * cos_theta - y * sin_theta + x0,
                x * sin_theta + y * cos_theta + y0)
    return xform


# ===========================================================
# Function: create sail
# ===========================================================
def create_sail( s1, s2, s3, s4, type, obj, my_tool, ship_name):

    texs_path = my_tool.texs_path
    sail_tex_def_str = my_tool.sail_tex_def_str or "parus_common.tga"
    flag_tex_def_str = my_tool.flag_tex_def_str or "flagall.tga"
    sail_quality = my_tool.sail_quality_int
    cloth_sail_bool = my_tool.cloth_sail_bool
    hull_num_int = my_tool.hull_num_int
    flag_type_int = my_tool.flag_type_int
    flag_num_int = (my_tool.flag_num_int)-1

    
    # -----------------------------------------------------------
    # Define sail object type
    # -----------------------------------------------------------
    if type == 't' or type == 'v':
        vertices = [s1, s2, s3]
        edges = []
        faces = [(0, 1, 2)]
        cloth_name = 'sail'
    elif type == 'd' or type == 'f' or type == 's' or type == 'g':
        vertices = [s1, s2, s3, s4]
        edges = []
        faces = [(0, 1, 2, 3)]
        cloth_name = 'sail'
    elif type == 'fp':
        vertices = [s1, s2, s3, s4]
        edges = []
        faces = [(0, 1, 2, 3)]
        cloth_name = 'flg'
        flag_type = 'penn'
    elif type == 'fl':
        vertices = [s1, s2, s3, s4]
        edges = []
        faces = [(0, 1, 2, 3)]
        cloth_name = 'flg'
        flag_type = 'flag'
    elif type == 'fs':
        vertices = [s1, s2, s3, s4]
        edges = []
        faces = [(0, 1, 2, 3)]
        cloth_name = 'flg'
        flag_type = 'sflag'


    # -----------------------------------------------------------
    # Define sail object name
    # -----------------------------------------------------------
    s_name = cloth_name + '_' + type
    sail_name = obj.name
    print('sail_name', sail_name)
    if fnmatch.fnmatchcase(obj.name, '*.*'):
        if fnmatch.fnmatchcase(obj.name, '*_*'):
            dot = obj.name.split('.', 1)[0]
            us = dot.split('_', 1)[1]
            final_sail_name = s_name + '' + us + '_' + (obj.name.split('.', 1)[1])
            # example, looking for this name: saild_1.001
        else:
            if fnmatch.fnmatchcase(obj.name, '*[0-9].[0-9]*'):
                dot = obj.name.split('.', 1)[0]
                #us = dot.split('_', 1)[1]
                final_sail_name = s_name + '' + (dot.replace(cloth_name + type, '')) + '_' + (obj.name.split('.', 1)[1])
                # example, looking for this name: saild5.001
            elif fnmatch.fnmatchcase(obj.name, '*.[0-9]*'):
                final_sail_name = s_name + '0_' + (obj.name.split('.', 1)[1])
                # example, looking for this name: saild.001
    else:
        if fnmatch.fnmatchcase(obj.name, '*[0-9]*'):
            if fnmatch.fnmatchcase(obj.name, '*_[0-9]*'):
                us = obj.name.split('_', 1)[1]
                final_sail_name = s_name + '' + us
                # example, looking for this name: saild_1
            elif fnmatch.fnmatchcase(obj.name, '*[0-9]*') and fnmatch.fnmatchcase(obj.name, 'penn*'):
                final_sail_name = s_name + '' + (sail_name.replace(flag_type, '')) + '_000'
                # example, looking for this name: penn1
            elif fnmatch.fnmatchcase(obj.name, '*[0-9]*') and fnmatch.fnmatchcase(obj.name, 'flag*'):
                final_sail_name = s_name + '' + (sail_name.replace(flag_type, '')) + '_000'
                # example, looking for this name: flag1
            elif fnmatch.fnmatchcase(obj.name, '*[0-9]*') and fnmatch.fnmatchcase(obj.name, 'sflag*'):
                final_sail_name = s_name + '' + (sail_name.replace(flag_type, '')) + '_000'
                # example, looking for this name: flag1
            else:
                final_sail_name = s_name + '' + (sail_name.replace(cloth_name + type, '')) + '_000'
                # example, looking for this name: saild1
        else:
            final_sail_name = s_name + '0_000'
            # example, looking for this name: saild

    print("Final sail name:", final_sail_name)


    # -----------------------------------------------------------
    # Create sail object
    # -----------------------------------------------------------
    new_mesh = bpy.data.meshes.new(s_name + '_mesh')
    new_mesh.from_pydata(vertices, edges, faces)
    new_mesh.update()

    # make object from mesh
    new_object = bpy.data.objects.new(final_sail_name, new_mesh)


    # -----------------------------------------------------------
    # Add sail object to existing collection
    # -----------------------------------------------------------
    sail_collection = bpy.data.collections[ship_name]
    sail_collection.objects.link(new_object)


    # -----------------------------------------------------------
    # Make sail object parent to sail dummy
    # -----------------------------------------------------------
    """
    parn = bpy.data.objects[obj.name]
    chld = bpy.data.objects[final_sail_name]
    bpy.ops.object.parent_clear({'selected_editable_objects': chld}, type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.parent_set({'object': parn, 'selected_editable_objects': chld})
    #chld.parent = parn
    """


    # Select sail object
    root_ob = bpy.context.scene.objects[final_sail_name] # Get the object
    bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
    bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
    root_ob.select_set(True)

    # Make shading smooth
    bpy.ops.object.shade_smooth()
    
    # Creating UV
    #bpy.ops.mesh.uv_texture_add()
    obj = bpy.data.objects[final_sail_name]
    obj.data.uv_layers.new(name = 'UVMap')
    uvMap = obj.data.uv_layers['UVMap']


    # Defines the pivot, scale and rotate UVs
    if type == 't' or type == 'v' or type == 'd' or type == 'f' or type == 's' or type == 'g':
        pivot = Vector( (0, 0.505) )
        scale = Vector( (1, -1.02492) )

    elif type == 'fl' or type == 'fp' or type == 'fs':
        ob_rot = bpy.context.object
        rad = radians(-90)
        anchor = (0.5, 0.5)

        rot = make_rotation_transformation(rad, anchor)

        UVmap = ob_rot.data.uv_layers.active
        for v in ob_rot.data.loops :
             UVmap.data[v.index].uv = rot(UVmap.data[v.index].uv )

        if flag_type_int == 1:
            pivot = Vector( (0.1428*flag_num_int, 0) )
            scale = Vector( (0.1242, 1) )
        elif flag_type_int == 2:
            pivot = Vector( (0.11121*flag_num_int, 0) )
            scale = Vector( (0.09992, 1) )
    
    ScaleUV( uvMap, scale, pivot )


    # -----------------------------------------------------------
    # Create material
    # -----------------------------------------------------------
    
    # Set texture
    if type == 't' or type == 'v' or type == 'd' or type == 'f' or type == 's' or type == 'g':
        mat_name = ship_name + '_Sail_Defaul_Mat'
        texture_file = sail_tex_def_str

    elif type == 'fl' or type == 'fp' or type == 'fs':
        mat_name = ship_name + '_Flag_Defaul_Mat'
        texture_file = flag_tex_def_str


    # -----------------------------------------------------------
    # Look for sail and flag textures if not found create default
    # -----------------------------------------------------------
    texture_path_found = None
    
    if sail_tex_def_str is not None:
        for ship_dir in Path(texs_path).rglob(f'**/{ship_name}'):
            for hull_dir in ([f'hull{hull_num_int}',] if hull_num_int is not None else []) + ['hull1']:
                if (ship_dir/hull_dir).exists() and (ship_dir/hull_dir/texture_file).exists():
                    texture_path_found = ship_dir/hull_dir/texture_file
                    break
            if texture_path_found is not None:
                break

        if texture_path_found is None:
            for ship_dir in Path(texs_path).rglob(f'**/{ship_name}'):
                for tex_file in ship_dir.rglob(f'**/{texture_file}'):
                    texture_path_found = tex_file
                    break
                if texture_path_found is not None:
                    break

        if texture_path_found is None:
            for ship_dir in Path(texs_path).rglob(f'**/{texture_file}'):
                texture_path_found = ship_dir
                break

    texture_path_found = texture_path_found or os.path.join(texs_path, texture_file)

    texture_path = str(texture_path_found)
    print(final_sail_name, 'use this texture:', texture_path)


    ac_ob = bpy.context.active_object

    # Get material
    mat = bpy.data.materials.get(mat_name)

    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.blend_method = 'CLIP'

        
        bsdf = find_principled_node(mat)
        if bsdf is None:
            raise TypeError("No Principled BSDF node found in the material")

        spec = find_specular_input(bsdf)
        if spec is None:
            raise TypeError("No Specular IOR Level input found in the material.")

        spec.default_value = 0.0

        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')

        if texture_file in bpy.data.images:
            texImage.image = bpy.data.images[texture_file]
        else:
            if os.path.isfile(texture_path):
                texImage.image = bpy.data.images.load(texture_path)
            else:
                placeholder_image = bpy.data.images.new(texture_file, width=1, height=1)
                placeholder_image.pixels = [0.5,0.5,0.5,1]
                texImage.image = placeholder_image

        mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
        mat.node_tree.links.new(bsdf.inputs['Alpha'], texImage.outputs['Alpha'])


    # Assign it to object
    if ac_ob.data.materials:
        # assign to 1st material slot
        ac_ob.data.materials[0] = mat
    else:
        # no slots
        ac_ob.data.materials.append(mat)


    # -----------------------------------------------------------
    # Change sail object origin (pivot)
    # -----------------------------------------------------------

    # give 3dcursor new coordinates
    bpy.context.scene.cursor.location = bpy.data.objects[sail_name].matrix_world.translation
    
    # set the origin on the current object to the 3dcursor location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    # set 3dcursor location back to the stored location
    bpy.context.scene.cursor.location = Vector((0.0,0.0,0.0))


    # -----------------------------------------------------------
    # Subdivide sail object
    # -----------------------------------------------------------
    if not sail_quality == 0:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.subdivide(number_cuts=sail_quality)
        bpy.ops.object.mode_set(mode="OBJECT")
    else:
        print('no subdivide')


    if cloth_sail_bool:
        # -----------------------------------------------------------
        # Make animated sail
        # -----------------------------------------------------------
        if not final_sail_name in bpy.context.scene.objects.keys():
            print('Nothinh to cloth. Are you sure you/ve generated sails already?')
        elif final_sail_name in bpy.context.scene.objects.keys():
            sailObj = bpy.data.objects[final_sail_name]
            sailMsh = sailObj.data

            # Define Vertex Group
            vg_name = 'PinSail'
            sailObj.vertex_groups.new(name = vg_name)

            # Define vertex index
            index_s1 = 0 # hard point
            index_s2 = 1 # hard point
            index_s3 = 2 # soft point
            index_s4 = 3 # soft point (only for rectangular sail)


            # -----------------------------------------------------------
            # Add proper vertices to Vertex Group
            # -----------------------------------------------------------
            other_indices = get_verts_in_line(sailMsh.vertices[index_s1], sailMsh.vertices[index_s2], sailMsh)

            if type == 't' or type == 'v':
                indices = [index_s1, index_s2, index_s3] + other_indices
            elif type == 'd' or type == 'f' or type == 's' or type == 'g':
                indices = [index_s1, index_s2, index_s3, index_s4] + other_indices
            elif type == 'fp' or type == 'fl' or type == 'fs':
                indices = [index_s1, index_s2] + other_indices

            sailObj.vertex_groups[vg_name].add(indices, 1, 'REPLACE')


            # -----------------------------------------------------------
            # Add cloth modifier
            # -----------------------------------------------------------
            
            # Set frame(1)
            bpy.context.scene.frame_set(1)

            # Add Cloth modifier to sail
            sailObj.modifiers.new('Cloth', 'CLOTH')
            sailObj.modifiers["Cloth"].settings.vertex_group_mass = vg_name

            if type == 't' or type == 'v' or type == 'd' or type == 'f' or type == 's' or type == 'g':
                sailObj.modifiers["Cloth"].settings.mass = 0.3 #kg
                sailObj.modifiers["Cloth"].settings.tension_stiffness = 15.0
                sailObj.modifiers["Cloth"].settings.compression_stiffness = 15.0
                sailObj.modifiers["Cloth"].settings.shear_stiffness = 0.001
                sailObj.modifiers["Cloth"].settings.bending_stiffness = 2.0
            elif type == 'fp' or type == 'fl' or type == 'fs':
                sailObj.modifiers["Cloth"].settings.mass = 0.01 #kg
                sailObj.modifiers["Cloth"].settings.tension_stiffness = 15.0
                sailObj.modifiers["Cloth"].settings.compression_stiffness = 15.0
                sailObj.modifiers["Cloth"].settings.shear_stiffness = 10
                sailObj.modifiers["Cloth"].settings.bending_stiffness = 2.0

    else:
        print(final_sail_name, 'will not be clothed')

    # Deseelct all
    bpy.ops.object.select_all(action='DESELECT')
    
    bpy.context.view_layer.update()


def define_sail_or_flag_points(ship_name, my_tool, clo_n, clo_ch_n, clo_t):

    # Check all objects in the scene
    for obj in bpy.context.scene.objects:
    
        sail_name = obj.name
        if obj.type != 'EMPTY':
            continue
        #print('Cloth start name:', clo_n)

        # Look for specific sail or flag name in all objects in the scene
        if fnmatch.fnmatchcase(obj.name, clo_n + '*') or fnmatch.fnmatchcase(obj.name, clo_n):

            #select sail
            root_ob = bpy.context.scene.objects[sail_name] # Get the object
            bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
            bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
            root_ob.select_set(True)

            # Select childrens
            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')

            # List of object references
            objs = bpy.context.selected_objects

            # If target found and object list not empty
            if objs:

                # Loop through all dummies (pointers) inside sail dummy
                # these dummies will angle points for creating sail mesh.
                # cp - for cloth point
                for o in objs:
                    if fnmatch.fnmatchcase(o.name, clo_ch_n + '1*'):
                        cp1_n = o.name
                    elif fnmatch.fnmatchcase(o.name, clo_ch_n + '2*'):
                        cp2_n = o.name
                    elif fnmatch.fnmatchcase(o.name, clo_ch_n + '3*'):
                        cp3_n = o.name
                    elif fnmatch.fnmatchcase(o.name, clo_ch_n + '4*'):
                        cp4_n = o.name
                    else:
                        print(clo_n, 'has no cloth points')

            # Define Vector for each cloth point
            if clo_t == 'd' or clo_t == 'f' or clo_t == 's' or clo_t == 'g':
                s1 = bpy.data.objects[cp1_n].matrix_world.translation
                s2 = bpy.data.objects[cp2_n].matrix_world.translation
                s3 = bpy.data.objects[cp3_n].matrix_world.translation
                s4 = bpy.data.objects[cp4_n].matrix_world.translation
                
                print('Vertex ID0:', clo_ch_n + '1:', cp1_n, s1)
                print('Vertex ID1:', clo_ch_n + '2:', cp2_n, s2)
                print('Vertex ID2:', clo_ch_n + '3:', cp3_n, s3)
                print('Vertex ID3:', clo_ch_n + '4:', cp4_n, s4)

            elif clo_t == 't' or clo_t == 'v':
                s1 = bpy.data.objects[cp1_n].matrix_world.translation
                s2 = bpy.data.objects[cp2_n].matrix_world.translation
                s3 = bpy.data.objects[cp3_n].matrix_world.translation
                s4 = ''
                
                print('Vertex ID0:', clo_ch_n + '1:', cp1_n, s1)
                print('Vertex ID1:', clo_ch_n + '2:', cp2_n, s2)
                print('Vertex ID2:', clo_ch_n + '3:', cp3_n, s3)

            elif clo_t == 'fp' or clo_t == 'fl' or clo_t == 'fs':
                s1 = bpy.data.objects[cp1_n].matrix_world.translation
                s2 = bpy.data.objects[cp4_n].matrix_world.translation
                s3 = bpy.data.objects[cp3_n].matrix_world.translation
                s4 = bpy.data.objects[cp2_n].matrix_world.translation
                
                print('Vertex ID0:', clo_ch_n + '1:', cp1_n, s1)
                print('Vertex ID3:', clo_ch_n + '4:', cp4_n, s2)
                print('Vertex ID2:', clo_ch_n + '3:', cp3_n, s3)
                print('Vertex ID1:', clo_ch_n + '2:', cp2_n, s4)


            # clo_t for clo_n:
            # 'd' for Saild   - rectangular sail
            # 't' for Sailt   - triangular sail
            # 'f' for Sailf   - rectangular sail
            # 'v' for Sailv   - triangular sail
            # 's' for Sails   - rectangular sail
            # 'g' for Sailg   - rectangular sail
            # 'fp' for penn   - rectangular flag (pennant, banner, long flag)
            # 'fl' for flag   - rectangular flag (common flag, short one)
            # 'fs' for Sflag  - rectangular flag (common flag, short one)
            create_sail(s1, s2, s3, s4, clo_t, obj, my_tool, ship_name)

            print('')


def create_dummy(collection_name, dummy_name, dummy_parent_name, dummy_location):

    # Set target collection to a known collection 
    coll_target = bpy.context.scene.collection.children.get(collection_name)

    # Create dummy helper for left bottom vant point (vp_lm_n)
    o = bpy.data.objects.new( dummy_name, None )
    coll_target.objects.link( o )
    o.empty_display_size = 0.5
    o.empty_display_type = 'ARROWS'
    bpy.data.objects[dummy_name].location = dummy_location

    # Parent vp_lm_n to 'vants' dummy
    a = bpy.data.objects[dummy_parent_name]
    b = bpy.data.objects[dummy_name]
    b.parent = a

    bpy.context.view_layer.update()

def get_wind_object():
    result = None
    for o in bpy.context.scene.objects:
        if o.type == 'EMPTY' and o.field is not None and o.field.type == 'WIND':
            result = o
            break
    return result

def import_and_assemble_ship(context):

    my_tool = context.scene.my_tool
    gen_rig_bool = my_tool.gen_rig_bool
    imp_ship_bool = my_tool.imp_ship_bool
    anim_sail_bool = my_tool.anim_sail_bool
    ship_path = my_tool.ship_path
    hull_num_int = my_tool.hull_num_int
    texs_path = my_tool.texs_path
    clear_scn_bool = my_tool.clear_scn_bool
    gen_sails_bool = my_tool.gen_sails_bool
    gen_flag_bool = my_tool.gen_flag_bool
    gen_penn_bool = my_tool.gen_penn_bool
    gen_vants_bool = my_tool.gen_vants_bool

    d = ship_path
    
    # Clear scene before loading new ship
    if clear_scn_bool:
        clear_scene()    

    # Define ship name (and collection name) from filepath
    ship_name = os.path.basename(os.path.normpath(d))
    print('Ship name: ' + ship_name)


    if imp_ship_bool:
        rem_default_coll()

        # -----------------------------------------------------------
        # Import ship hull from *.gm file
        # -----------------------------------------------------------
        for (dirpath, dirnames, filenames) in os.walk(d):
            print ("dirpath:", dirpath)
            #print ("filenames:", filenames[2])
            #print(os.path.splitext(filenames[1])[-1])

        #import main hull
        main_hull = d + '\\' + ship_name + '.gm'
        print('Ship main hull: ' + main_hull)
        getattr(bpy.ops, 'import').gm(
            filepath = main_hull,
            textures_path = texs_path,
            hull_num_int = hull_num_int
            )
        # bpy.ops.import.gm(filepath = f) doesn't work directly
        
        bpy.context.view_layer.update()


        # -----------------------------------------------------------
        # Collect ship part names from *.gm files into array
        # -----------------------------------------------------------
        ob_names_set = set()

        for gm_file in Path(ship_path).rglob(f'**/*{ship_name}*.gm'):    
            #print('File path:', file)

            filepath_split = os.path.split(gm_file)[1]
            #print('Full filename:', filepath_split)
            
            file_name = filepath_split.split('.', 1)[0]
            #print("Filename only:", file_name)

            #get object name from filename
            obj_name = ((file_name.lower()).replace((ship_name.lower()) + '_', ''))
            #print('Object name (without the first part): ' + obj_name)

            ob_names_set.add(obj_name)

        ob_names_set.remove(ship_name.lower())

        print(len(ob_names_set), ob_names_set)
        print('')

        while True:
            added = set()
            for ob_name in ob_names_set:
                file = ship_path + '\\' + ship_name + '_' + ob_name + ".gm"
                is_added = import_objects(ob_name, file, ship_name, my_tool)
                if is_added:
                    added.add(ob_name)
            if len(added) == 0:
                break
            ob_names_set.difference_update(added)

        if len(ob_names_set) > 0:
            print('Warning: ({}) has not been attached'.format(ob_names_set))
        else:
            print('All parts has been inserted')

        # -----------------------------------------------------------
        # Hide path geometry
        # -----------------------------------------------------------
        path = bpy.context.scene.objects.get('path')
        if path:
            root_ob = bpy.context.scene.objects['path'] # Get the object
            bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
            bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
            root_ob.select_set(True)

            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')
            for o in bpy.context.selected_objects: o.hide_set(True)

    else:
        print('ship will not be loaded')


    # -----------------------------------------------------------
    # Build vants
    # -----------------------------------------------------------
    if gen_vants_bool:
        print('Do vants here')

        # Check all objects in the scene
        for obj in bpy.context.scene.objects:
            v_ch = 'vant'
            sh_n = 'shroud'
            st_n = 'stave'
            vp_add_arr = [1, 2, 3]
            
            vants_dummy_name = 'vants'
            rig_type_shroud = 'v_rope'
            rig_type_stave = 'stave'

            # Look for specific vant name in all objects in the scene
            if fnmatch.fnmatchcase(obj.name, v_ch + '[0-9]' + 'u'):

                vp_u_n = obj.name # vant point top
                vp_r_n = vp_u_n.replace('u', 'r') # vant point bottom right
                vp_l_n = vp_u_n.replace('u', 'l') # vant point bottom left
                v_num = (vp_u_n.replace('u', '')).replace(v_ch, '') # vant num
                vp_rm_n = v_ch + v_num + 'rt' # vant point top right
                vp_lm_n = v_ch + v_num + 'lt' # vant point top left
                
                vr_r_n = v_ch + '_' + v_num + '_' + sh_n + '_r'
                vr_l_n = v_ch + '_' + v_num + '_' + sh_n + '_l'
                vr_tr_n = v_ch + '_' + v_num + '_' + sh_n + '_tr'
                vr_tl_n = v_ch + '_' + v_num + '_' + sh_n + '_lr'
                vstave_n = v_ch + '_' + v_num + '_' + st_n
                vp_add_n = v_ch + '_' + v_num + '_' + st_n + '_'

                v1 = bpy.data.objects[vp_u_n].matrix_world.translation
                v2 = bpy.data.objects[vp_r_n].matrix_world.translation
                v3 = bpy.data.objects[vp_l_n].matrix_world.translation

                # Specify vant helper (vp_rm_n and vp_lm_n) shift and height
                v_height = 0.8
                v_shift = 0.4

                #print('Vant number', v_num + ':', vp_u_n, vp_r_n, vp_l_n, vp_rm_n, vp_lm_n)
                print('')


                # -----------------------------------------------------------
                # Create vant helpers
                # -----------------------------------------------------------

                # Create dummy helper for right bottom vant point (vp_rm_n)
                v4_loc = v2 - (v2-v1)*v_height + Vector((-v_shift*(-1 if v2.y < 0 else 1),0,0))
                create_dummy(ship_name, vp_rm_n, vants_dummy_name, v4_loc)
                
                # Create dummy helper for left bottom vant point (vp_lm_n)
                v5_loc = v3 - (v3-v1)*v_height + Vector((v_shift*(-1 if v3.y < 0 else 1),0,0))
                create_dummy(ship_name, vp_lm_n, vants_dummy_name, v5_loc)

                v4 = bpy.data.objects[vp_rm_n].matrix_world.translation
                v5 = bpy.data.objects[vp_lm_n].matrix_world.translation


                for i in range(len(vp_add_arr)):
                    vp_add_loc = v4 + ((v5-v4)/3) * (vp_add_arr[i])
                    create_dummy(ship_name, vp_add_n + str(vp_add_arr[i]), vants_dummy_name, vp_add_loc)




                """
                # Create dummy helper test
                vp_add_loc = v4 + ((v4-v5)/3) * 1
                create_dummy(ship_name, v_test_n, vants_dummy_name, vp_add_loc)
                """


                # -----------------------------------------------------------
                # Process vant creation through functions
                # -----------------------------------------------------------


                """
                creating_rope(context, vp_r_n, vp_rm_n, v_num, rig_type_shroud, vants_dummy_name, ship_name, vr_r_n)
                creating_rope(context, vp_l_n, vp_lm_n, v_num, rig_type_shroud, vants_dummy_name, ship_name, vr_l_n)
                creating_rope(context, vp_rm_n, vp_u_n, v_num, rig_type_shroud, vants_dummy_name, ship_name, vr_tr_n)
                creating_rope(context, vp_lm_n, vp_u_n, v_num, rig_type_shroud, vants_dummy_name, ship_name, vr_tl_n)
                creating_rope(context, vp_lm_n, vp_rm_n, v_num, rig_type_stave, vants_dummy_name, ship_name, vstave_n)
                """








                """
                # -----------------------------------------------------------
                # Create vant top object
                # -----------------------------------------------------------
                final_top_vant_name = v_ch + '_' + v_num + '_top'
                final_bot_vant_name = v_ch + '_' + v_num + '_bottom'
                print('Final vant top name:', final_top_vant_name)
                print('Final vant bottom name:', final_bot_vant_name)
            
                vertices = [v1, v4, v5]
                edges = []
                faces = [(0, 1, 2)]

                new_mesh = bpy.data.meshes.new(v_ch + '_top_' + v_num + '_mesh')
                new_mesh.from_pydata(vertices, edges, faces)
                new_mesh.update()

                # make object from mesh
                new_object = bpy.data.objects.new(final_top_vant_name, new_mesh)

                # Add sail object to existing collection
                sail_collection = bpy.data.collections[ship_name]
                sail_collection.objects.link(new_object)

                # Select sail object
                vant_ob = bpy.context.scene.objects[final_top_vant_name] # Get the object
                bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
                bpy.context.view_layer.objects.active = vant_ob # Make the cube the active object 
                vant_ob.select_set(True)

                # Make shading smooth
                bpy.ops.object.shade_smooth()
                
                # Creating UV
                bpy.ops.mesh.uv_texture_add()
                vant_ob = bpy.data.objects[final_top_vant_name]
                uvMap = vant_ob.data.uv_layers['UVMap']


                # -----------------------------------------------------------
                # Create vant bottom object
                # -----------------------------------------------------------
                vertices = [v3, v2, v4, v5]
                edges = []
                faces = [(0, 1, 2, 3)]

                new_mesh = bpy.data.meshes.new(v_ch + '_bottom_' + v_num + '_mesh')
                new_mesh.from_pydata(vertices, edges, faces)
                new_mesh.update()

                # make object from mesh
                new_object = bpy.data.objects.new(final_bot_vant_name, new_mesh)

                # Add sail object to existing collection
                sail_collection = bpy.data.collections[ship_name]
                sail_collection.objects.link(new_object)

                # Select sail object
                vant_ob = bpy.context.scene.objects[final_bot_vant_name] # Get the object
                bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
                bpy.context.view_layer.objects.active = vant_ob # Make the cube the active object 
                vant_ob.select_set(True)

                # Make shading smooth
                bpy.ops.object.shade_smooth()
                
                # Creating UV
                bpy.ops.mesh.uv_texture_add()
                vant_ob = bpy.data.objects[final_bot_vant_name]
                uvMap = vant_ob.data.uv_layers['UVMap']
                """

        #define_vant_points(ship_name, my_tool)








    # -----------------------------------------------------------
    # Generate rig
    # -----------------------------------------------------------
    if gen_rig_bool:
        # -----------------------------------------------------------
        # Creat 'rig' dummy
        # -----------------------------------------------------------
        rig_dummy_name = 'rig'
        o = bpy.data.objects.new( rig_dummy_name, None )

        # due to the new mechanism of "collection"
        bpy.context.scene.collection.objects.link( o )

        # empty_draw was replaced by empty_display
        o.empty_display_size = 2
        o.empty_display_type = 'PLAIN_AXES'

        # Set target collection to a known collection 
        coll_target = bpy.context.scene.collection.children.get(ship_name)

        root_ob = bpy.context.scene.objects[rig_dummy_name] # Get the object
        bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
        bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
        root_ob.select_set(True)

        # List of object references
        objs = bpy.context.selected_objects

        # If target found and object list not empty
        if coll_target and objs:

            # Loop through all objects
            for o in objs:
                # Loop through all collections the obj is linked to
                for coll in o.users_collection:
                    # Unlink the object
                    coll.objects.unlink(o)

                # Link each object to the target collection
                coll_target.objects.link(o)

        a = bpy.data.objects['root']
        b = bpy.data.objects[rig_dummy_name]
        b.parent = a


        # -----------------------------------------------------------
        # Build a rig
        # -----------------------------------------------------------
        for obj in bpy.context.scene.objects:

            # rig for rope(s)
            if fnmatch.fnmatchcase(obj.name, "ropeb*"):
                rig_type = 'rope'
                rope_start_name = obj.name
                print ('Rope start name:', rope_start_name)

                rope_num = rope_start_name.split('b', 1)[1]
                print('Rope number:', rope_num)

                rope_end_name = rig_type + 'e' + rope_num

                found = False
                for o in bpy.context.scene.objects:
                    if o.name == rope_end_name:
                        creating_rope(context, rope_start_name, rope_end_name, rope_num, rig_type, rig_dummy_name, ship_name, '')
                        found = True
                        break

                if not found:
                    print('Abort creating rope:', rope_start_name, 'exists,', 'but', rope_end_name, 'is not in the scene')

            # rig for fal(s)
            elif fnmatch.fnmatchcase(obj.name, "falb*"):
                rig_type = 'fal'
                fal_start_name = obj.name
                print ('Fal start name:', fal_start_name)

                fal_num = fal_start_name.split('b', 1)[1]
                print('Fal number:', fal_num)

                fal_end_name = rig_type + 'e' + fal_num

                found = False
                for o in bpy.context.scene.objects:
                    if o.name == fal_end_name:
                        creating_rope(context, fal_start_name, fal_end_name, fal_num, rig_type, rig_dummy_name, ship_name, '')
                        found = True
                        break

                if not found:
                    print('Abort creating rope(fal):', fal_start_name, 'exists,', 'but', fal_end_name, 'is not in the scene')

    else:
        print('rig will not be created')


    # -----------------------------------------------------------
    # Build sails, flags and pennats
    # -----------------------------------------------------------

    # define_sail_or_flag_points(dummy name, sub-dummy name, type for cloth object's name)
    # scipt will look for object with specified dummy names and will try to build cloth object
    s_ch = 'sail'
    f_ch = 'f'
    
    if gen_sails_bool:
        define_sail_or_flag_points(ship_name, my_tool, 'saild', s_ch, 'd') # 4 points
        define_sail_or_flag_points(ship_name, my_tool, 'sailf', s_ch, 'f') # 4 points
        define_sail_or_flag_points(ship_name, my_tool, 'sails', s_ch, 's') # 4 points
        define_sail_or_flag_points(ship_name, my_tool, 'sailg', s_ch, 'g') # 4 points
        define_sail_or_flag_points(ship_name, my_tool, 'sailt', s_ch, 't') # 3 points
        define_sail_or_flag_points(ship_name, my_tool, 'sailv', s_ch, 'v') # 3 points
    if gen_penn_bool:
        define_sail_or_flag_points(ship_name, my_tool, 'penn', f_ch, 'fp') # 4 points
    if gen_flag_bool:
        define_sail_or_flag_points(ship_name, my_tool, 'flag', f_ch, 'fl') # 4 points
        define_sail_or_flag_points(ship_name, my_tool, 'sflag', f_ch, 'fs') # 4 points


    # -----------------------------------------------------------
    # Animate sails
    # -----------------------------------------------------------
    if anim_sail_bool:
        # Add wind to scene
        bpy.ops.object.effector_add(type='WIND')

        root_ob = get_wind_object()
        if root_ob is None:
            raise TypeError('Wind not found')
        root_ob.field.strength = 65.0

        # Select wind
        bpy.ops.object.select_all(action='DESELECT') # Deselect all objects
        bpy.context.view_layer.objects.active = root_ob # Make the cube the active object 
        root_ob.select_set(True)

        # Rotate wind object
        bpy.context.active_object.rotation_euler[1] = math.radians(84)

        if wind_dir == 'l':
            bpy.context.active_object.rotation_euler[2] = math.radians(14)
        elif wind_dir == 'r':
            bpy.context.active_object.rotation_euler[2] = math.radians(-14)
        elif wind_dir == 'c':
            bpy.context.active_object.rotation_euler[2] = math.radians(0)

        # Start Animation
        bpy.ops.screen.animation_play()

        # Stop animation (at frame 30 - would be enough for a good sail shape)
        bpy.app.handlers.frame_change_pre.append(stop_playback)


        # -----------------------------------------------------------
        # Apply all modifiers and remove wind after 1 sec (30 frames)
        # -----------------------------------------------------------
        for obj in bpy.context.scene.objects:

            # look for rectangular sail of type D
            if fnmatch.fnmatchcase(obj.name, "sail_d*") or fnmatch.fnmatchcase(obj.name, "sail_s*") or fnmatch.fnmatchcase(obj.name, "sail_g*") or fnmatch.fnmatchcase(obj.name, "sail_f*") or fnmatch.fnmatchcase(obj.name, "sail_t*") or fnmatch.fnmatchcase(obj.name, "sail_v*") or fnmatch.fnmatchcase(obj.name, "flg_fp*") or fnmatch.fnmatchcase(obj.name, "flg_fl*") or fnmatch.fnmatchcase(obj.name, "flg_fs*"):

                # Wait 1 sec (30 frames) then apply modifiers
                bpy.app.timers.register(functools.partial(apply_m, obj.name), first_interval=1)

    else:
        print('Sails will not be animated')


    print('===================================================================')
    print('')



# ------------------------------------------------------------------------
#     Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    ImpSEShip_Button,
    SETUP_PT_ImpSEShip,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        
    del bpy.types.Scene.my_tool
    
if __name__ == "__main__":
    register()
    
# Test call
#bpy.ops.impseship.main()

print("===================================================================")
print("")