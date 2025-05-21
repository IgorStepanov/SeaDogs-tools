import math
import os
import struct
import time

import bmesh
import bpy
import mathutils
import json
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, axis_conversion

bl_info = {
    "name": "SeaDogs Merge AN",
    "description": "Merge AN files",
    "author": "Artess999/Wazar",
    "version": (0, 0, 1),
    "blender": (4, 4, 1),
    "location": "File > Import",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import",
}


convert_rules = {
    'woman_to_man': {
        0: 1,
        1: 3,
        2: 4,
        11: 0,
        12: 0,
        3: 4,
        4: 3,
        5: 2,
        
        13: 7,
        16: 11,
        21: 16,
        
        17: 13,
        22: 38,
        26: 54,
        27: 54,
        28: 54,
        32: 81,
        33: 66,
        36: 91,
        37: 91,
        
        18: 12,
        23: 37,
        29: 53,
        30: 53,
        31: 53,
        34: 76,
        35: 65,
        38: 86,
        39: 86,
        
        6: 3,
        14: 8,
        19: 14,
        24: 19,
        7: 4,
        15: 9,
        20: 15,
        25: 20,
        8: 6,
        9: 4,
        10: 3
    },
    'jess_to_woman': {
      0: 0,
      1: 1,
      2: 2,
      3: 3,
      4: 4,
      5: 5,
      6: 6,
      7: 7,
      8: 8,
      9: 9,
      10: 10,
      11: 9,
      
      
      12: 11,
      13: 12,
      14: 13,
      15: 14,
      16: 6,
      17: 15,
      18: 7,
      19: 16,
      20: 17,
      21: 18,
      22: 19,
      
      
      23: 20,
      24: 21,
      
      25: 22,
      26: 23,
      27: 24,
      28: 25,
      29: None,
      30: 26,
      31: 27,
      32: 28,
      33: 29,
      34: 30,
      35: 31,
      36: None,
      37: 32,
      37: 32,
      38: 33,
      39: 33,
      40: 34,
      41: 35,
      42: 35,
      43: None,
      44: 36,
      45: 37,
      46: 38,
      47: 39,
      48: None
    },
    'danny_to_woman': {
        0: 0,
        1: 0,
        4: 7,
        9: 15,
        15: 20,
        20: 25,
        26: None,
        3: 6,
        8: 14,
        14:19,
        19:24,
        25: None,
        2: 5,
        7:13,
        11:16,
        16:21,
        12:18,
        13:17
    },
    'danny_to_man': {
      0:0,
      1:1,
      2:2,
      7:7,
      11:11,
      16:16,
      21:21,
      22: None,
      38: None,
      55: None,
      68: None,
      79: None,
      27:26,
      28:27,
      29:28,
      30:29,
      31:30,
      32:31,
      33:32,
      34:33,
      35:34,
      36:35,
      37:36,
      41:39,
      42:40,
      58:55,
      71:67,
      59:56,
      72:68,
      43:41,
      44:42,
      45:43,
      46:44,
      47:45,
      60:57,
      73:69,
      61:58,
      74:70,
      62:59,
      75:71,
      63:60,
      64:61,
      48:46,
      49:47,
      50:48,
      65:62,
      76:72,
      66:63,
      77:73,
      67:64,
      78:74,
      51:49,
      52:50,
      53:51,
      54:52,

      12:12,
      17:17,
      23:22,
      39:37,
      56:53,
      69:65,
      80:75,
      81:76,
      82:77,
      83:78,
      84:79,
      90:85,
      100:95,
      110:105,
      91:86,
      92:87,
      93:88,
      94:89,
      101:96,
      102:97,
      103:98,
      104:99,
      111:106,
      112:107,
      113:108,
      114:109,
      120:115,
      121:116,
      122:117,
      123:118,
      
      13:13,
      18:18,
      24:23,
      40:38,
      57:54,
      70:66,
      
      85:80,
      86:81,
      87:82,
      88:83,
      89:84,
      
      95:90,
      96:91,
      97:92,
      98:93,
      99:94,
      
      105:100,
      106:101,
      107:102,
      108:103,
      109:104,
      
      115:110,
      116:111,
      117:112,
      118:113,
      119:114,
      
      124:119,
      125:120,
      126:121,
      127:122,
      
      3:3,
      8:8,
      14:14,
      19:19,
      25:24,
      
      4:4,
      9:9,
      15:15,
      20:20,
      26:25,
      
      5:5,
      10:10,
      
      6:6
    }
}



#{
#	"name": "Normal to fight_mus",
#	"length": 25,
#	"first_frame": {
#		"top_file": "Rumba.an",
#		"top_frame": 2235,
#		"top_convert_rule": "danny_to_woman",
#		"bottom_file": "Rumba.an",
#		"bottom_frame": 2235
#		"bottom_convert_rule": "danny_to_man"
#	},
#	"last_frame": {
#		"top_file": "mushketer_whisper.an",
#		"top_frame": 2050,
#		"top_convert_rule": "danny_to_woman",
#		"bottom_file": "mushketer_whisper.an",
#		"bottom_frame": 2050
#		"bottom_convert_rule": "danny_to_man"
#	}
#}
def convertNode(node, rule):
    if rule is None:
        return node
    convert_rule = convert_rules[rule]
    return convert_rule[node]
    
def convertNodeMerge(node):
    #return node
    strNode = danny_to_woman[node]
    if strNode is None:
        return None
    return int(strNode)


correction_matrix = axis_conversion(
    from_forward='X', from_up='Y', to_forward='Y', to_up='Z')

def read_vector(file):
    x = struct.unpack("<f", file.read(4))[0]
    y = struct.unpack("<f", file.read(4))[0]
    z = struct.unpack("<f", file.read(4))[0]
    return [x, y, z]

def read_d3dx_quaternion(file):
    x = struct.unpack("<f", file.read(4))[0]
    y = struct.unpack("<f", file.read(4))[0]
    z = struct.unpack("<f", file.read(4))[0]
    w = struct.unpack("<f", file.read(4))[0]
    return [w, x, y, z]

def parse_an(file_path=""):
    with open(file_path, mode='rb') as file:
        frames_quantity = struct.unpack("<l", file.read(4))[0]
        joints_quantity = struct.unpack("<l", file.read(4))[0]
        fps = struct.unpack("<f", file.read(4))[0]

        parent_indices = []
        for i in range(joints_quantity):
            idx = struct.unpack("<l", file.read(4))[0]
            parent_indices.append(idx)

        start_joints_positions = []
        for i in range(joints_quantity):
            vector = read_vector(file)
            start_joints_positions.append(vector)

        blender_start_joints_positions = []
        for i in range(joints_quantity):
            if i == 0:
                blender_start_joints_positions.append(
                    start_joints_positions[0])
            else:
                [x, y, z] = start_joints_positions[i]
                [dX, dY, dZ] = blender_start_joints_positions[parent_indices[i]]
                blender_start_joints_positions.append([x + dX, y + dY, z + dZ])

        root_bone_positions = []
        [root_start_x, root_start_y, root_start_z] = start_joints_positions[0]
        for i in range(frames_quantity):
            [x, y, z] = read_vector(file)
            root_bone_positions.append(
                [x - root_start_x, y - root_start_y, z - root_start_z])

        joints_angles = []
        for i in range(joints_quantity):
            joints_angles.append([])
            for j in range(frames_quantity):
                d3dx_quaternion = read_d3dx_quaternion(file)
                joints_angles[i].append(d3dx_quaternion)

    return {
        "header": {
            "nFrames": frames_quantity,
            "nJoints": joints_quantity,
            "framesPerSec": fps,
        },
        "parentIndices": parent_indices,
        "startJointsPositions": start_joints_positions,
        "blenderStartJointsPositions": blender_start_joints_positions,
        "rootBonePositions": root_bone_positions,
        "jointsAngles": joints_angles,
    }



class AN:
    def __init__(self, fname, wdir):
    
        path = os.path.join(wdir, fname)
        self.data = parse_an(path)
        self.header = self.data.get('header')
        self.frames_quantity = self.header.get('nFrames')
        self.joints_quantity = self.header.get('nJoints')
        self.fps = int(self.header.get('framesPerSec'))
        self.joints_angles = self.data.get('jointsAngles')
        self.root_bone_positions = self.data.get('rootBonePositions')
        
        
        
def import_an(report_func, context, file_path=""):

    working_dir = os.path.dirname(file_path)

    cookbook = None
    with open(file_path, 'r') as file:
        cookbook = json.load(file)
    
    main_file = cookbook['main_file']
    
    file_name = os.path.basename(main_file)[:-3]
    an_files = {}
    an_files[main_file] = AN(main_file, working_dir)
    data = an_files[main_file].data
    top_nodes = cookbook['top_nodes']
    default_frame = cookbook['default_frame']
    append_list = []
    additional_frames = 0
    if 'append_list' in cookbook:
        append_list = cookbook['append_list']
        for elem in append_list:
            an_files[elem['file']] = AN(elem['file'], working_dir)
            additional_frames += an_files[elem['file']].frames_quantity

    
    
    merge_list = []
    if 'merge_list' in cookbook:
        merge_list = cookbook['merge_list']
        for elem in merge_list:
            if elem['top_file'] not in an_files:
                an_files[elem['top_file']] = AN(elem['top_file'], working_dir)
            if elem['bottom_file'] not in an_files:
                an_files[elem['bottom_file']] = AN(elem['bottom_file'], working_dir)
            if elem['bottom_frames'][1] - elem['bottom_frames'][0] != elem['top_frames'][1] - elem['top_frames'][0]:
                report_func({'ERROR'}, "frame count mistmatch")
                return {'CANCELLED'} 
            additional_frames += elem['bottom_frames'][1] - elem['bottom_frames'][0]

    patch_list = []
    if 'patch_list' in cookbook:
        patch_list = cookbook['patch_list']
        for elem in patch_list:
            if elem['first_frame']['top_file'] not in an_files:
                an_files[elem['first_frame']['top_file']] = AN(elem['first_frame']['top_file'], working_dir)
            if elem['first_frame']['bottom_file'] not in an_files:
                an_files[elem['first_frame']['bottom_file']] = AN(elem['first_frame']['bottom_file'], working_dir)
            if elem['last_frame']['top_file'] not in an_files:
                an_files[elem['last_frame']['top_file']] = AN(elem['last_frame']['top_file'], working_dir)
            if elem['last_frame']['bottom_file'] not in an_files:
                an_files[elem['last_frame']['bottom_file']] = AN(elem['last_frame']['bottom_file'], working_dir)
            additional_frames += elem['length']
    header = data.get('header')
    frames_quantity = header.get('nFrames')
    joints_quantity = header.get('nJoints')
    fps = int(header.get('framesPerSec'))

    parent_indices = data.get('parentIndices')
    start_joints_positions = data.get('startJointsPositions')
    blender_start_joints_positions = data.get('blenderStartJointsPositions')
    root_bone_positions = data.get('rootBonePositions')
    joints_angles = data.get('jointsAngles')

    bpy.context.scene.frame_set(0)
    bpy.context.scene.render.fps = fps
    bpy.context.scene.frame_start = 0
    
    frame_end = frames_quantity + additional_frames
    
    bpy.context.scene.frame_end = frame_end - 1

    collection = bpy.data.collections.new(file_name)
    bpy.context.scene.collection.children.link(collection)

    armature = bpy.data.armatures.new('armature')
    armature_obj = bpy.data.objects.new('armature_obj', armature)
    collection.objects.link(armature_obj)

    animation_data = armature_obj.animation_data_create()
    action = bpy.data.actions.new(name="Joints_action")
    animation_data.action = action
    slot = action.slots.new(id_type='OBJECT', name="Joints_slot")
    layer = action.layers.new("Joints_Layer")
    animation_data.action_slot = slot
    strip = layer.strips.new(type='KEYFRAME')
    channelbag = strip.channelbag(slot, ensure=True)

    armature_obj.data.display_type = 'STICK'

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    armature_edit_bones = armature_obj.data.edit_bones

    bones_arr = []

    for idx in range(joints_quantity):
        bone = armature_edit_bones.new("Bone" + str(idx))

        if idx != 0:
            bone.parent = bones_arr[parent_indices[idx]]

        pos = mathutils.Vector(start_joints_positions[idx])
        prepared_pos = mathutils.Vector(blender_start_joints_positions[idx])
        parent_pos = mathutils.Vector(
            blender_start_joints_positions[parent_indices[idx]])

        if idx in parent_indices:
            child_idx = parent_indices.index(idx)
            child_pos = mathutils.Vector(
                blender_start_joints_positions[child_idx])
        else:
            child_pos = mathutils.Vector(
                prepared_pos) + mathutils.Vector([0, 0.00001, 0])

        bone.head = (prepared_pos[0],
                     prepared_pos[1] - 0.00001, prepared_pos[2])
        bone.tail = (prepared_pos[0],
                     prepared_pos[1] + 0.00001, prepared_pos[2])

        bone.matrix = correction_matrix.to_4x4() @ bone.matrix

        bones_arr.append(bone)

    bpy.ops.object.mode_set(mode='POSE', toggle=False)

    for bone_idx in range(joints_quantity):
        bone_name = "Bone" + str(bone_idx)

        if bone_idx == 0:
            for idx in range(3):
                fc = channelbag.fcurves.new(
                    'pose.bones["' + bone_name + '"].location', index=idx)
                fc.keyframe_points.add(count=frame_end)

                key_values = []
                
                for frame in range(frames_quantity):
                    key_values.append(frame)
                    key_values.append(root_bone_positions[frame][idx])
                total_quantity = frames_quantity
                
                for elem in append_list:
                    append_file = elem['file']
                    total_quantity += an_files[append_file].frames_quantity
                    for frame in range(an_files[append_file].frames_quantity):
                        key_values.append(frame + frames_quantity)
                        key_values.append(an_files[append_file].root_bone_positions[frame][idx])
                        
                        
                for elem in merge_list:
                    frames_elem = None
                    anim_file = None
                    if bone_idx in top_nodes:
                        frames_elem = 'top_frames'
                        anim_file = elem['top_file']
                        pass
                    else:
                        frames_elem = 'bottom_frames'
                        anim_file = elem['bottom_file']
                        pass
                        
                    if frames_elem is not None:
                        frame_count = elem[frames_elem][1] - elem[frames_elem][0] + 1
                        print('"{}": {}'.format(elem['name'], total_quantity))
                        frame_start = elem[frames_elem][0]
                        for frame in range(frame_count):
                            key_values.append(frame + total_quantity)
                            key_values.append(an_files[anim_file].root_bone_positions[frame + frame_start][idx])
                        total_quantity += frame_count
                            
                for elem in patch_list:
                    frame_elem = None
                    anim_file_elem = None
                    if bone_idx in top_nodes:
                        frame_elem = 'top_frame'
                        anim_file_elem = 'top_file'
                        pass
                    else:
                        frame_elem = 'top_frame'
                        anim_file_elem = 'bottom_file'
                        pass
                        
                    if frame_elem is not None:

                        print('"{}": {}'.format(elem['name'], total_quantity))
                        
                        key_values.append(total_quantity)
                        key_values.append(an_files[elem['first_frame'][anim_file_elem]].root_bone_positions[elem['first_frame'][frame_elem]][idx])
                        for frame in range(elem['length'] - 2): 
                            key_values.append(total_quantity + frame + 1)
                            key_values.append(an_files[elem['last_frame'][anim_file_elem]].root_bone_positions[elem['last_frame'][frame_elem]][idx])
                        key_values.append(total_quantity + elem['length'] - 1)
                        key_values.append(an_files[elem['last_frame'][anim_file_elem]].root_bone_positions[elem['last_frame'][frame_elem]][idx])
                        total_quantity += elem['length']

                fc.keyframe_points.foreach_set("co", key_values)

                fc.update()

        
        for idx in range(4):
            fc = channelbag.fcurves.new(
                'pose.bones["' + bone_name + '"].rotation_quaternion', index=idx)
            fc.keyframe_points.add(count=frame_end)

            key_values = []
            for frame in range(frames_quantity):
                key_values.append(frame)
                key_values.append(joints_angles[bone_idx][frame][idx])
            total_quantity = frames_quantity
            #print(frames_quantity)
            #print(an_files[add_an].frames_quantity)
            print('"base frames_quantity": {}'.format(frames_quantity))
            
            for elem in append_list:
                append_file = elem['file']
                total_quantity += an_files[append_file].frames_quantity
                alt_bone_idx = convertNode(bone_idx, elem['convert_rule'])
                for frame in range(an_files[append_file].frames_quantity):
                    if alt_bone_idx is not None:
                        key_values.append(frame + frames_quantity)
                        key_values.append(an_files[append_file].joints_angles[alt_bone_idx][frame][idx])
                    else:
                        key_values.append(frame + frames_quantity)
                        key_values.append(joints_angles[bone_idx][default_frame][idx])

            for elem in merge_list:
                frames_elem = None
                anim_file = None
                m_bone_idx = bone_idx
                if bone_idx in top_nodes:
                    frames_elem = 'top_frames'
                    anim_file = elem['top_file']
                    m_bone_idx = convertNode(bone_idx, elem['top_convert_rule'])
                else:
                    frames_elem = 'bottom_frames'
                    anim_file = elem['bottom_file']
                    m_bone_idx = convertNode(bone_idx, elem['bottom_convert_rule'])

                frame_count = elem[frames_elem][1] - elem[frames_elem][0] + 1
                print('"{}": {}'.format(elem['name'], total_quantity))
                frame_start = elem[frames_elem][0]
                for frame in range(frame_count):
                    if m_bone_idx is not None:
                        key_values.append(frame + total_quantity)
                        angles = an_files[anim_file].joints_angles
                        bone_angles = angles[m_bone_idx]
                        frame_angles = bone_angles[frame + frame_start]
                        key_values.append(frame_angles[idx])
                    else:
                        key_values.append(frame + frames_quantity)
                        key_values.append(joints_angles[bone_idx][default_frame][idx])
                total_quantity += frame_count
                    
            for elem in patch_list:
                frame_elem = None
                anim_file_elem = None
                convert_rule_str = None
                if bone_idx in top_nodes:
                    frame_elem = 'top_frame'
                    anim_file_elem = 'top_file'
                    convert_rule_str = 'top_convert_rule'
                else:
                    frame_elem = 'bottom_frame'
                    anim_file_elem = 'bottom_file'
                    bottom_convert_rule = 'top_convert_rule'
                    
                first_frame_bone_idx = convertNode(bone_idx, elem['first_frame'][convert_rule_str])
                last_frame_bone_idx = convertNode(bone_idx, elem['last_frame'][convert_rule_str])
                
                print('"{}": {}'.format(elem['name'], total_quantity))
                
                key_values.append(total_quantity)
                key_values.append(an_files[elem['first_frame'][anim_file_elem]].joints_angles[first_frame_bone_idx][elem['first_frame'][frame_elem]][idx])
                for frame in range(elem['length'] - 2): 
                    key_values.append(total_quantity + frame + 1)
                    key_values.append(0)
                key_values.append(total_quantity + elem['length'] - 1)
                key_values.append(an_files[elem['last_frame'][anim_file_elem]].joints_angles[last_frame_bone_idx][elem['last_frame'][frame_elem]][idx])
                total_quantity += elem['length']
                    
            print(len(key_values))
            fc.keyframe_points.foreach_set("co", key_values)

            fc.update()

    """ armature_obj.rotation_euler[0] = math.radians(90)
    armature_obj.rotation_euler[2] = math.radians(90) """

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return {'FINISHED'}


class ImportAn(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import.an"
    bl_label = "Merge AN"

    # ImportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )


    def execute(self, context):
        return import_an(self.report, context, self.filepath)


def menu_func_import(self, context):
    self.layout.operator(ImportAn.bl_idname,
                         text="AN Merge(.json)")


def register():
    bpy.utils.register_class(ImportAn)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportAn)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
