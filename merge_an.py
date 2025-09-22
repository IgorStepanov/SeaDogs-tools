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
    "author": "Artess999, Wazar",
    "version": (1, 1, 0),
    "blender": (4, 4, 1),
    "location": "File > Import",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import",
}

SkipKey = 'skip'
NoTransformation = (1.0, 0.0, 0.0, 0.0)


convert_rules = {
    'woman_to_man': {
        0: 1,
        1: 3,
        2: 4,
        11: None,#3,
        12: None, #4,
        3: 4,
        4: 3,
        5: 2,
        
        13: 7,
        16: 11,
        21: 16,
        
        17: 13,
        22: 18,
        26: 38,
        27: None,
        28: None,
        32: 66,
        33: None,
        36: 91,
        37: None,
        
        18: 12,
        23: 17,
        29: 37,
        30: None,
        31: None,
        34: 65,
        35: None,
        38: 86,
        39: None,
        
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
        2: 5,
        3: 6,
        4: 7,

        6:8,
        7:13,
        11:16,
        16:21,
        9: 15,
        15: 20,
        20: 25,
        26: None,
        
        8: 14,
        14:19,
        19:24,
        25: None,
        
        
        
        12:18,
        
        
        
        13:17,
        18:22,
        40:26,
        70:32,
        96:36,
        
        12:18,
        17:23,
        39:29,
        69:34,
        91:38
        
    },
    
    
    
    
    
    
    
    
    'danny_to_jess': {
        0:0,
        1:0,
        3:6,
        8:15,
        14:22,
        19:27,
        4:7,
        9:17,
        15:23,
        20:28,
        6:8,
        2:5,
        7:14,
        11:19,
        16:24,
        22:29,
        38:36,
        55:43,
        68:48,
        13:20,
        18:25,
        40:30,
        70:37,
        96:44,
        12:21,
        17:26,
        39:33,
        69:40,
        91:46,
        
        
        24:SkipKey,
        57:SkipKey,
        23:SkipKey,
        56:SkipKey
        
    },
    
    
    'man_to_woman': {
        0: 0,
        #1: 0,
        2: 5,
        
        
        #ноги
        3: 6,
        8: 14,
        14:19,
        19:24,

        4: 7,
        9: 15,
        15: 20,
        20: 25,

        6:8,
        
        #тело
        7:13,
        11:16,
        16:21,
        
        
        
        
        
        #руки
        12:18,
        17:23,
        37:29,
        65:34,
        85:38,
        86:38,
        87:38,
        88:38,
        89:38,
        
        13:17,
        18:22,
        38:26,
        66:32,
        
        90:36,
        91:36,
        92:36,
        93:36,
        94:36
        

        
        
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
    },
    
    'danny_to_sd2_woman': {
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
        10:10,
        11:11,
        12:12,
        13:13,
        14:14,
        15:15,
        16:16,
        17:17,
        18:18,
        19:19,
        20:20,
        
        22:21,
        38:26,
        55:29,
        68:32,
        79:35,
        
        23:22,
        39:27,
        56:30,
        69:33,
        
        80:36,
        81:37,
        82:38,
        83:39,
        84:40,
        
        90:46,
        91:47,
        92:48,
        93:49,
        94:50,

        100:56,
        101:57,
        102:58,
        103:59,
        104:60,
        
        110:66,
        111:67,
        112:68,
        113:69,
        114:70,
        
        120:76,
        121:77,
        122:78,
        123:79,

        24:23,
        40:28,
        57:31,
        70:34,
        
        85:41,
        86:42,
        87:43,
        88:44,
        89:45,
        
        95:51,
        96:52,
        97:53,
        98:54,
        99:55,
        
        
        105:61,
        106:62,
        107:63,
        108:64,
        109:65,
        
        115:71,
        116:72,
        117:73,
        118:74,
        119:75,
        
        124:80,
        125:81,
        126:82,
        127:83,
        
        26:25,
        25:24
    },
    
    'sd2_woman_to_danny': {
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
        10:10,
        11:11,
        12:12,
        13:13,
        14:14,
        15:15,
        16:16,
        17:17,
        18:18,
        19:19,
        20:20,
        21:22,
        26:38,
        29:55,
        32:68,
        35:79,
        22:23,
        27:39,
        30:56,
        33:69,
        36:80,
        37:81,
        38:82,
        39:83,
        40:84,
        46:90,
        47:91,
        48:92,
        49:93,
        50:94,
        56:100,
        57:101,
        58:102,
        59:103,
        60:104,
        66:110,
        67:111,
        68:112,
        69:113,
        70:114,
        76:120,
        77:121,
        78:122,
        79:123,
        
        23:24,
        28:40,
        31:57,
        34:70,
        41:85,
        42:86,
        43:87,
        44:88,
        45:89,
        51:95,
        52:96,
        53:97,
        54:98,
        55:99,
        61:105,
        62:106,
        63:107,
        64:108,
        65:109,
        71:115,
        72:116,
        73:117,
        74:118,
        75:119,
        80:124,
        81:125,
        82:126,
        83:127,
        25:26,
        24:25 
    },
    'sd2_piratess_to_danny': {
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
        10:10,
        11:11,
        12:12,
        13:13,
        14:14,
        15:15,
        16:16,
        17:17,
        18:18,
        19:19,
        20:20,
        
        
        
        

        21:23,
        25:39,
        27:56,
        29:69,
        
        
        
        31:80,
        32:81,
        33:82,
        34:83,
        35:84,
        
        41:90,
        42:91,
        43:92,
        44:93,
        45:94,
        
        51:100,
        52:101,
        53:102,
        54:103,
        55:104,
        
        61:110,
        62:111,
        63:112,
        64:113,
        65:114,
        
        71:120,
        72:121,
        73:122,
        74:123,
        
        22:24,
        26:40,
        28:57,
        30:70,
        
        36:85,
        37:86,
        38:87,
        39:88,
        40:89,
        46:95,
        47:96,
        48:97,
        49:98,
        50:99,
        56:105,
        57:106,
        58:107,
        59:108,
        60:109,
        66:115,
        67:116,
        68:117,
        69:118,
        70:119,
        75:124,
        76:125,
        77:126,
        78:127,
        
        24:26,
        23:25 
    },
    'sd2_man_to_man': {
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
        10:10,
        11:11,
        12:12,
        13:13,
        14:14,
        15:15,
        16:16,
        17:17,
        18:18,
        19:19,
        20:20,
        
        
        
        

        21:22,
        25:37,
        27:53,
        29:65,
        
        
        
        31:75,
        32:76,
        33:77,
        34:78,
        35:79,
        
        41:85,
        42:86,
        43:87,
        44:88,
        45:89,
        
        51:95,
        52:96,
        53:97,
        54:98,
        55:99,
        
        61:105,
        62:106,
        63:107,
        64:108,
        65:109,
        
        71:115,
        72:116,
        73:117,
        74:118,
        
        22:23,
        26:38,
        28:54,
        30:66,
        
        36:80,
        37:81,
        38:82,
        39:83,
        40:84,
        
        46:90,
        47:91,
        48:92,
        49:93,
        50:94,
        
        56:100,
        57:101,
        58:102,
        59:103,
        60:104,
        
        66:110,
        67:111,
        68:112,
        69:113,
        70:114,
        
        75:119,
        76:120,
        77:121,
        78:122,
        
        24:25,
        23:24 
    }
}


fix_rules = {
    'jess_fix_hair': {
        22: lambda a, j, fn : transform_hair_jess(a, j, 22)
    },
    'hand_make_straight': {
        39: lambda a, j, fn : hand_make_straight(a, j, 56, fn, 39),
        56: lambda a, j, fn : a if fn == 0 else j[56][0],
        69: lambda a, j, fn : hand_make_straight(a, j, 56, fn, 69),
        40: lambda a, j, fn : hand_make_straight(a, j, 57, fn, 40),
        57: lambda a, j, fn : a if fn == 0 else j[57][0],
        70: lambda a, j, fn : hand_make_straight(a, j, 57, fn, 70)
    },

}


def transform_hair_jess(point_q, joints, bone_num):
    first_needed_q = mathutils.Quaternion((-0.340719, -0.606968, 0.338404, 0.633232))
    first_real_q = mathutils.Quaternion((joints[bone_num][0][0], joints[bone_num][0][1], joints[bone_num][0][2], joints[bone_num][0][3]))
    current_real_q = mathutils.Quaternion((point_q[0], point_q[1], point_q[2], point_q[3]))
    
    transform_q = first_needed_q @ first_real_q.inverted()
    current_needed_q = transform_q @ current_real_q
    return current_needed_q
    
    
def hand_make_straight(point_q, joints, middle_num, fn, bone_num):
    if fn == 0:
        return point_q
    first_needed_q = mathutils.Quaternion((joints[middle_num][0][0], joints[middle_num][0][1], joints[middle_num][0][2], joints[middle_num][0][3]))
    first_real_q = mathutils.Quaternion((joints[middle_num][fn][0], joints[middle_num][fn][1], joints[middle_num][fn][2], joints[middle_num][fn][3]))
    
    current_real_q = mathutils.Quaternion((point_q[0], point_q[1], point_q[2], point_q[3]))
    
    transform_q = first_real_q @ first_needed_q.inverted()
    
    exp_avg = (transform_q.to_exponential_map() +
               first_needed_q.to_exponential_map()) / 2 # +
                   #shift.to_exponential_map()) / 3
        
    half_transform_q = mathutils.Quaternion(exp_avg)
    
    current_needed_q = half_transform_q @ current_real_q


    if bone_num == 69 and fn >= 13319 and fn <= 13345:
        base_frame = 13324
        base_q = mathutils.Quaternion((0.527591, -0.425861, -0.734265, -0.033846))
        calculated_base_q = hand_make_straight(joints[69][base_frame], joints, middle_num, base_frame, -1)
        transform_q = base_q @ calculated_base_q.inverted()
        current_needed_q = transform_q @ current_needed_q


    return current_needed_q
    

def transform_point_skirt(point_q, base_num, joints, mod_num, direction, rot = None):
    a1 = mathutils.Quaternion((joints[base_num][0][0], joints[base_num][0][1], joints[base_num][0][2], joints[base_num][0][3]))
    a2 = mathutils.Quaternion((point_q[0], 2*point_q[1], point_q[2], 2*point_q[3]))
    b1 = mathutils.Quaternion((joints[mod_num][0][0], joints[mod_num][0][1], joints[mod_num][0][2], joints[mod_num][0][3]))
    
    if point_q[1] > 0 and direction == 'f':
        return b1
    elif point_q[1] < 0 and direction == 'b':
        return b1 
    a2a1 = a2 @ a1.inverted()
    
    b2 = a2a1 @ b1
    
    
    leg_q = mathutils.Quaternion((point_q[0], point_q[1], point_q[2], point_q[3]))
    leg_xr = abs(leg_q.to_euler('XYZ')[0])
    
    x_mod = leg_xr / math.radians(45.0)
    
    if rot is not None:
        e = b2.to_euler('XYZ')
        e[0] += x_mod * rot[0]
        e[1] += rot[1]
        e[2] += rot[2]
        
        b2 = e.to_quaternion()
    return b2 


def danny_transform_point_legs(point_q, joints, frame, direction, bone):
    left_leg = mathutils.Quaternion((joints[3][frame][0], joints[3][frame][1], joints[3][frame][2], joints[3][frame][3]))
    left_leg_p2 = mathutils.Quaternion((joints[8][frame][0], joints[8][frame][1], joints[8][frame][2], joints[8][frame][3]))
    right_leg = mathutils.Quaternion((joints[4][frame][0], joints[4][frame][1], joints[4][frame][2], joints[4][frame][3]))
    right_leg_p2 = mathutils.Quaternion((joints[9][frame][0], joints[9][frame][1], joints[9][frame][2], joints[9][frame][3]))

    left_leg_angle = -left_leg.to_euler('XYZ')[0]
    right_leg_angle = -right_leg.to_euler('XYZ')[0]

    left_leg_p2_angle = -left_leg_p2.to_euler('XYZ')[0]
    right_leg_p2_angle = -right_leg_p2.to_euler('XYZ')[0]


    leg_x_diff = right_leg_angle - left_leg_angle
    leg_x_diff /= 16

    leg_diff = abs(right_leg_angle) + abs(right_leg_p2_angle) - abs(left_leg_angle) - abs(left_leg_p2_angle)

    if direction == 'r':
        leg_diff *= -1
        leg_x_diff *= -1

    leg_diff /= 32

    max_diff = math.radians(4.0)
    min_diff = -max_diff
    if leg_diff < min_diff:
        leg_diff = min_diff
    elif leg_diff > max_diff:
        leg_diff = max_diff


    max_x_diff = math.radians(6.0)
    min_x_diff = -max_diff
    if leg_x_diff < min_x_diff:
        leg_x_diff = min_x_diff
    elif leg_x_diff > max_x_diff:
        leg_x_diff = max_x_diff  

    y_diff = 0
    if bone == 3:
        y_diff = -math.radians(4.0)
    elif bone == 4:
        y_diff = math.radians(4.0)

    target_q = mathutils.Quaternion((point_q[0], point_q[1], point_q[2], point_q[3]))

    e = target_q.to_euler('XYZ')
    e[0] += leg_x_diff 
    e[1] += y_diff
    e[2] += leg_diff
    target_q = e.to_quaternion()

    if frame >= 26688 and frame <= 26704:
        print ('frame walk: {}, leg_diff: {}'.format(frame, math.degrees(leg_diff)))

    if frame >= 21728 and frame <= 21740:
        print ('frame run: {}, leg_diff: {}'.format(frame, math.degrees(leg_diff)))
    return target_q 



def danny_transform_point_hair(point_q, joints, frame, bone):
    shift = mathutils.Quaternion((0.99996, -0.000843, -0.00577, -0.006859))
    n_11_1 = mathutils.Quaternion((joints[11][0][0], joints[11][0][1], joints[11][0][2], joints[11][0][3]))
    n_11_2 = mathutils.Quaternion((joints[11][frame][0], joints[11][frame][1], joints[11][frame][2], joints[11][frame][3]))

    n_16_1 = mathutils.Quaternion((joints[16][0][0], joints[16][0][1], joints[16][0][2], joints[16][0][3]))
    n_16_2 = mathutils.Quaternion((joints[16][frame][0], joints[16][frame][1], joints[16][frame][2], joints[16][frame][3]))

    target_q = mathutils.Quaternion((point_q[0], point_q[1], point_q[2], point_q[3]))

    n11_tr = n_11_2 @ n_11_1.inverted()
    n16_tr = n_16_2 @ n_16_1.inverted()

    #n11_tr = n11_tr
    #n16_tr = n16_tr
    tr = n16_tr @ n11_tr.inverted()
    if bone == 38:

        angle_1 = tr @ target_q
        angle_2 = tr.inverted() @ target_q
        exp_avg = (angle_1.to_exponential_map() +
                   angle_2.to_exponential_map()) / 2.5 # +
                   #shift.to_exponential_map()) / 3
        
        target_q = mathutils.Quaternion(exp_avg)
        #target_q = n11_tr @ target_q
        #target_q = n16_tr @ target_q

    return target_q 




def transform_point_fixed(point_q, angles):

    target_q = mathutils.Quaternion((point_q[0], point_q[1], point_q[2], point_q[3]))

    e = target_q.to_euler('XYZ')

    e[0] += angles[0]
    e[1] += angles[1]
    e[2] += angles[2]

    target_q = e.to_quaternion()

    return target_q 


def fix_danny_jess_hair(point_q, joints, old_joints, bone_new, bone_old):
    a1 = mathutils.Quaternion((joints[bone_new][0][0], joints[bone_new][0][1], joints[bone_new][0][2], joints[bone_new][0][3]))
    a2 = mathutils.Quaternion((old_joints[bone_old][0][0], old_joints[bone_old][0][1], old_joints[bone_old][0][2], old_joints[bone_old][0][3]))
    b1 = mathutils.Quaternion((point_q[0], 2*point_q[1], point_q[2], 2*point_q[3]))

    a2a1 = a2 @ a1.inverted()
    
    b2 = a2a1 @ b1
    return b2


anim_modifiers = {
    'woman_to_man': {
        1: lambda a, j, f, oj : transform_point_skirt(a, 6, oj, 1, 'f', (math.radians(60.0), 0.0, 0.0)), #[a[0], -1*a[1], -1 * a[0], 4 * a[3]],# [0.724759 - 1.0, -0.013815, -0.009461, -0.688799],
        2: lambda a, j, f, oj : transform_point_skirt(a, 7, oj, 2, 'f', (math.radians(-60.0), 0.0, 0.0)), #[a[0], -1*a[1], -1 * a[0], 4 * a[3]],# [0.658084 - 1.0, -0.022546, 0.011745, -0.752515],
        #11: [0.707107 - 1.0, 0, 0, 0.707107],
        #12: [0.707197 - 1.0, -0.000041, 0.00017, 0.707017],
        3: lambda a, j, f, oj : transform_point_skirt(a, 7, oj, 3, 'b'), #[0.998278 - 1.0, -0.002846, -0.042357, -0.040493],
        4: lambda a, j, f, oj : transform_point_skirt(a, 6, oj, 4, 'b'), #[0.974792 - 1.0, 0.038104, -0.211684, -0.059318]
        
        9: lambda a, j, f, oj : transform_point_skirt(a, 7, oj, 9, '', (0.0, math.radians(-20.0), 0.0)), #[2*a[0], 0, -2*a[0], -2*a[0]],# [0.658084 - 1.0, -0.022546, 0.011745, -0.752515],
        10: lambda a, j, f, oj : transform_point_skirt(a, 6, oj, 10, '', (0.0, math.radians(20.0), 0.0)) #[2*a[0], 0, 2*a[0], 2*a[0]]# [0.724759 - 1.0, -0.013815, -0.009461, -0.688799],
    },
    'danny_to_man': {
        1: lambda a, j, frame, oj : danny_transform_point_legs(a, j, frame, 'f', 1),
        2: lambda a, j, frame, oj : danny_transform_point_legs(a, j, frame, 'r', 2),
        3: lambda a, j, frame, oj : danny_transform_point_legs(a, j, frame, 'r', 3),
        4: lambda a, j, frame, oj : danny_transform_point_legs(a, j, frame, 'r', 4),

        #22: lambda a, j, frame, oj : transform_hair_jess(a, oj, 22),
        38: lambda a, j, frame, oj : danny_transform_point_hair(a, j, frame, 38),
        68: lambda a, j, frame, oj : danny_transform_point_hair(a, j, frame, 68),

        #69: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-1.94789), math.radians(18.06650), math.radians(-1.6005))),
        70: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-1.94789), math.radians(18.06650), math.radians(-1.6005))) 
            if (frame >= 24533 and frame <= 24593) or (frame >= 32689 and frame <= 32720) else a,

        #56: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-4.25439), math.radians(-6.56844), math.radians(-5.5424))),
        57: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-4.25439), math.radians(-6.56844), math.radians(-5.5424))) 
            if (frame >= 24533 and frame <= 24593) or (frame >= 32689 and frame <= 32720) else a,

        #39: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(46.92019), math.radians(-29.39333), math.radians(73.92513))),
        40: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(5.42489), math.radians(-23.59684), math.radians(17.122033))) 
            if (frame >= 24533 and frame <= 24593) or (frame >= 32689 and frame <= 32720) else a,

        #23: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(0.27161), math.radians(11.62612), math.radians(-13.56011))),
        24: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(0.27161), math.radians(11.62612), math.radians(-13.56011))) 
            if (frame >= 24533 and frame <= 24593) or (frame >= 32689 and frame <= 32720) else a,

        #17: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-1.394899), math.radians(1.9225509), math.radians(2.55450999))),
        18: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-1.394899), math.radians(1.9225509), math.radians(2.55450999))) 
            if (frame >= 24533 and frame <= 24593) or (frame >= 32689 and frame <= 32720) else a,



        #18: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(100), math.radians(100), math.radians(100))),

        #39: lambda a, j, frame, oj : transform_point_fixed(a, (0, math.radians(-30), math.radians(14.9))),
        #40: lambda a, j, frame, oj : transform_point_fixed(a, (0, math.radians(-30), math.radians(14.9))),

        #23: lambda a, j, frame, oj : transform_point_fixed(a, (0, math.radians(18.5), 0)),
        #24: lambda a, j, frame, oj : transform_point_fixed(a, (0, math.radians(18.5), 0)),
        #17: lambda a, j, frame, oj : transform_point_fixed(a, (0, 0, math.radians(-3.2))),
        #18: lambda a, j, frame, oj : transform_point_fixed(a, (0, 0, math.radians(-3.2))),
        #56: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-1.51761), math.radians(-3.32716), math.radians(-5.71581))),
        #57: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-1.51761), math.radians(-3.32716), math.radians(-5.71581))),

        #69: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-3.4223), math.radians(-18.6995), math.radians(11.52168))),
        #70: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(-3.4223), math.radians(-18.6995), math.radians(11.52168)))
        #69: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(13.7423), math.radians(-26.88879), math.radians(7.12545))),
        #70: lambda a, j, frame, oj : transform_point_fixed(a, (math.radians(13.7423), math.radians(-26.88879), math.radians(7.12545)))

    },
    'danny_to_jess': {
        22: lambda a, j, frame, oj : fix_danny_jess_hair(a, j, oj, convert_node(22, 'danny_to_jess'), 22),
        38: lambda a, j, frame, oj : fix_danny_jess_hair(a, j, oj, convert_node(38, 'danny_to_jess'), 38),
        55: lambda a, j, frame, oj : fix_danny_jess_hair(a, j, oj, convert_node(55, 'danny_to_jess'), 55),
        68: lambda a, j, frame, oj : fix_danny_jess_hair(a, j, oj, convert_node(68, 'danny_to_jess'), 68)
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
def convert_node(node, rule):
    if rule is None:
        return node
    convert_rule = convert_rules[rule]
    
    if node not in convert_rule:
        return None
    return convert_rule[node]
    


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
        

def convert_fix_rule(fix_rule, point_q, joints, bone_num, frame_num):
    if fix_rule is None:
        return point_q
    if bone_num not in fix_rule:
        return point_q
    return fix_rule[bone_num](point_q, joints, frame_num)
        
def import_an(report_func, context, file_path=""):

    working_dir = os.path.dirname(file_path)

    cookbook = None
    with open(file_path, 'r') as file:
        cookbook = json.load(file)
    
    main_file = cookbook['main_file']
    ignore_original = False
    
    if 'ignore_original' in cookbook:
        ignore_original = cookbook['ignore_original']

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

    need_patch_zero = 'patch_zero' in cookbook
    patch_zero_rule = None
    patch_zero_file = None
    generate_patch = False
    
    if need_patch_zero:
        patch_zero_file_name = cookbook['patch_zero']['file']
        if patch_zero_file_name not in an_files:
            an_files[patch_zero_file_name] = AN(patch_zero_file_name, working_dir)
        patch_zero_file = an_files[patch_zero_file_name]
        if 'convert_rule' in cookbook['patch_zero']:
            patch_zero_rule = cookbook['patch_zero']['convert_rule']
        if 'generate_patch_file' in cookbook['patch_zero'] and cookbook['patch_zero']['generate_patch_file']:  
            generate_patch = True
            
    fix_rule = None
    if 'fix_rule' in cookbook:
        fix_rule = fix_rules[cookbook['fix_rule']]
    
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
    
    

    needed_frames = None
    frame_count_stripped = None
    if 'frame_ranges' in cookbook:
        frame_count_stripped = 0
        needed_frames = [0]*frames_quantity
        frame_ranges = cookbook['frame_ranges']
        for r in frame_ranges:
            start = r[0]
            end = r[1]
            if end > frames_quantity:
                report_func({'ERROR'}, "frame count is lower than range {}".format(r))
                return {'CANCELLED'} 
            for i in range(start, end):
                needed_frames[i] = True
                frame_count_stripped += 1
    base_frames_quantity = frames_quantity
    if frame_count_stripped is not None:
        base_frames_quantity = frame_count_stripped
    if ignore_original:
        base_frames_quantity = 0
    frame_end = base_frames_quantity + additional_frames
    if generate_patch:
        frame_end = 2
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

    res_message = ""
    for bone_idx in range(joints_quantity):
        bone_name = "Bone" + str(bone_idx)

        if bone_idx == 0:
            for idx in range(3):
                fc = channelbag.fcurves.new(
                    'pose.bones["' + bone_name + '"].location', index=idx)
                fc.keyframe_points.add(count=frame_end)

                key_values = []
                total_quantity = 0
                if ignore_original:
                    frames_quantity = 0
                else:
                    cur_idx = 0
                    for frame in range(frames_quantity):
                        if frame == 0 and need_patch_zero:
                            key_values.append(0)
                            key_values.append(patch_zero_file.root_bone_positions[0][idx])
                            if generate_patch:
                                key_values.append(1)
                                key_values.append(root_bone_positions[0][idx])
                                break
                        else:   
                            if needed_frames is None or needed_frames[frame]:
                                key_values.append(cur_idx)
                                key_values.append(root_bone_positions[frame][idx])
                                cur_idx += 1
                    total_quantity = frames_quantity
                
                if not generate_patch:
                    for elem in append_list:
                        append_file = elem['file']
                        
                        for frame in range(an_files[append_file].frames_quantity):
                            if (frame + total_quantity) == 0 and need_patch_zero:
                                key_values.append(0)
                                key_values.append(patch_zero_file.root_bone_positions[0][idx])
                            else:
                                key_values.append(frame + total_quantity)
                                key_values.append(an_files[append_file].root_bone_positions[frame][idx])
                        if idx == 0:
                            res_message += '"{}" start: {}\n'.format(append_file, total_quantity)
                        total_quantity += an_files[append_file].frames_quantity
                        
                if not generate_patch:     
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
                            if idx == 0:
                                res_message += '"{}": {}\n'.format(elem['name'], total_quantity)
                            frame_start = elem[frames_elem][0]
                            for frame in range(frame_count):
                                if (frame + total_quantity) == 0 and need_patch_zero:
                                    key_values.append(0)
                                    key_values.append(patch_zero_file.root_bone_positions[0][idx])
                                else:
                                    key_values.append(frame + total_quantity)
                                    key_values.append(an_files[anim_file].root_bone_positions[frame + frame_start][idx])
                            total_quantity += frame_count
                  

                if not generate_patch:
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
                            if idx == 0:
                                res_message += '"{}": {}\n'.format(elem['name'], total_quantity)
                            
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

        fq = None

        for idx in range(4):
            fc = channelbag.fcurves.new(
                'pose.bones["' + bone_name + '"].rotation_quaternion', index=idx)
            fc.keyframe_points.add(count=frame_end)

            key_values = []
            total_quantity = 0
            if ignore_original:
                frames_quantity = 0
            else:
                cur_idx = 0
                for frame in range(frames_quantity):
                    if frame == 0 and need_patch_zero:
                        alt_bone_idx = convert_node(bone_idx, patch_zero_rule)
                        key_values.append(0)
                        if alt_bone_idx == SkipKey:
                            key_values.append(NoTransformation[idx]) 
                        elif alt_bone_idx is not None:
                            key_values.append(patch_zero_file.joints_angles[alt_bone_idx][0][idx])
                        else:
                            key_values.append(joints_angles[bone_idx][default_frame][idx])
                            
                        if generate_patch:
                            key_values.append(1)
                            transform = convert_fix_rule(fix_rule, joints_angles[bone_idx][0], joints_angles, bone_idx, frame)
                            key_values.append(transform[idx])
                            break
                    else:
                        if needed_frames is None or needed_frames[frame]:
                            key_values.append(cur_idx)
                            transform = convert_fix_rule(fix_rule, joints_angles[bone_idx][frame], joints_angles, bone_idx, frame)
                            try:
                                key_values.append(transform[idx])
                            except TypeError as e:
                                print('fix_rule = {}'.format(fix_rule))
                                print('transform = {}'.format(transform))
                                print('joints_angles[bone_idx][frame] = {}'.format(joints_angles[bone_idx][frame]))
                                print('idx = {}'.format(idx))
                                raise e
                            cur_idx += 1
                total_quantity = frames_quantity
            #print(frames_quantity)
            #print(an_files[add_an].frames_quantity)
            fq = frames_quantity
            
            if not generate_patch:
                for elem in append_list:
                    append_file = elem['file']
                    an_file = an_files[append_file]
                    #if idx == 0:
                    #    print('"{}" start: {}'.format(append_file, total_quantity))
                    convert_rule = elem['convert_rule']
                    alt_bone_idx = convert_node(bone_idx, convert_rule)
                    modifiers = None
                    if convert_rule in anim_modifiers:
                        modifiers = anim_modifiers[convert_rule]
                    for frame in range(an_file.frames_quantity):
                        if (frame + total_quantity) == 0 and need_patch_zero:
                            alt_bone_idx = convert_node(bone_idx, patch_zero_rule)
                            key_values.append(0)
                            if alt_bone_idx == SkipKey:
                                key_values.append(NoTransformation[idx]) 
                            elif alt_bone_idx is not None:
                                key_values.append(patch_zero_file.joints_angles[alt_bone_idx][0][idx])
                            else:
                                key_values.append(joints_angles[bone_idx][default_frame][idx])
                        else:
                            key_values.append(frame + total_quantity)

                            if alt_bone_idx == SkipKey:
                                key_values.append(NoTransformation[idx]) 
                            elif alt_bone_idx is not None:
                                transform = an_file.joints_angles[alt_bone_idx][frame]
                                if modifiers is not None and bone_idx in modifiers:
                                    transform = modifiers[bone_idx](transform, an_file.joints_angles, frame, joints_angles)
                                transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, frame + total_quantity)
                                key_values.append(transform[idx])
                            else:
                                transform = joints_angles[bone_idx][default_frame]
                                if modifiers is not None and bone_idx in modifiers:
                                    transform = modifiers[bone_idx](transform, an_file.joints_angles, frame, joints_angles)
                                transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, frame + total_quantity)
                                key_values.append(transform[idx])
                    total_quantity += an_file.frames_quantity

            if not generate_patch:
                for elem in merge_list:
                    frames_elem = None
                    anim_file = None
                    m_bone_idx = bone_idx
                    convert_rule = None
                    if bone_idx in top_nodes:
                        frames_elem = 'top_frames'
                        anim_file = elem['top_file']
                        convert_rule = elem['top_convert_rule']
                    else:
                        frames_elem = 'bottom_frames'
                        anim_file = elem['bottom_file']
                        convert_rule = elem['bottom_convert_rule']

                    m_bone_idx = convert_node(bone_idx, convert_rule)
                    frame_count = elem[frames_elem][1] - elem[frames_elem][0] + 1
                    #if idx == 0:
                    #    print('"{}": {}'.format(elem['name'], total_quantity))
                    frame_start = elem[frames_elem][0]
                    for frame in range(frame_count):
                        if (frame + total_quantity) == 0 and need_patch_zero:
                            alt_bone_idx = convert_node(bone_idx, patch_zero_rule)
                            key_values.append(0)
                            if alt_bone_idx == SkipKey:
                                key_values.append(NoTransformation[idx]) 
                            elif alt_bone_idx is not None:
                                key_values.append(patch_zero_file.joints_angles[alt_bone_idx][0][idx])
                            else:
                                key_values.append(joints_angles[bone_idx][default_frame][idx])
                        else:
                            key_values.append(frame + total_quantity)
                            if m_bone_idx is not None:
                                transform = an_files[anim_file].joints_angles[m_bone_idx][frame + frame_start]
                                if convert_rule in anim_modifiers and bone_idx in anim_modifiers[convert_rule]:
                                    #transform = anim_modifiers[convert_rule][bone_idx](transform, joints_angles)
                                    transform = anim_modifiers[convert_rule][bone_idx](transform, an_files[anim_file].joints_angles[m_bone_idx], frame + frame_start, joints_angles)
                                transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, frame + total_quantity)
                                key_values.append(transform[idx])
                            else:
                                transform = joints_angles[bone_idx][default_frame]
                                if convert_rule in anim_modifiers and bone_idx in anim_modifiers[convert_rule]:
                                    transform = anim_modifiers[convert_rule][bone_idx](transform, an_files[anim_file].joints_angles[m_bone_idx], frame + frame_start, joints_angles)
                                transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, frame + total_quantity)
                                key_values.append(transform[idx])
                                #key_values.append(joints_angles[bone_idx][default_frame][idx])
                    total_quantity += frame_count
                    
                    
            if not generate_patch:
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
                    first_convert_rule = elem['first_frame'][convert_rule_str]
                    first_frame_bone_idx = convert_node(bone_idx, first_convert_rule)
                    last_convert_rule = elem['last_frame'][convert_rule_str]
                    last_frame_bone_idx = convert_node(bone_idx, last_convert_rule)
                    #if idx == 0:
                    #    print('"{}": {}'.format(elem['name'], total_quantity))
                    
                    key_values.append(total_quantity)
                    if first_frame_bone_idx is not None:
                        transform = an_files[elem['first_frame'][anim_file_elem]].joints_angles[first_frame_bone_idx][elem['first_frame'][frame_elem]]
                        if first_convert_rule in anim_modifiers and bone_idx in anim_modifiers[first_convert_rule]:
                            transform = anim_modifiers[first_convert_rule][bone_idx](transform, an_files[elem['first_frame'][anim_file_elem]].joints_angles, elem['first_frame'][frame_elem], joints_angles)
                        transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, total_quantity)
                        key_values.append(transform[idx])
                    else:
                        transform = joints_angles[bone_idx][default_frame]
                        if first_convert_rule in anim_modifiers and bone_idx in anim_modifiers[first_convert_rule]:
                            transform = anim_modifiers[first_convert_rule][bone_idx](transform, an_files[elem['first_frame'][anim_file_elem]].joints_angles, elem['first_frame'][frame_elem], joints_angles)
                        transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, total_quantity)
                        key_values.append(transform[idx])

                    key_values.append(total_quantity + elem['length'] - 1)
                    
                    if last_frame_bone_idx is not None:
                        transform = an_files[elem['last_frame'][anim_file_elem]].joints_angles[last_frame_bone_idx][elem['last_frame'][frame_elem]]
                        if last_convert_rule in anim_modifiers and bone_idx in anim_modifiers[last_convert_rule]:
                            transform = anim_modifiers[last_convert_rule][bone_idx](transform, an_files[elem['last_frame'][anim_file_elem]].joints_angles, elem['last_frame'][frame_elem], joints_angles)
                        transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, total_quantity + elem['length'] - 1)
                        key_values.append(transform[idx])
                    else:
                        transform = joints_angles[bone_idx][default_frame]
                        if last_convert_rule in anim_modifiers and bone_idx in anim_modifiers[last_convert_rule]:
                            transform = anim_modifiers[last_convert_rule][bone_idx](transform, an_files[elem['last_frame'][anim_file_elem]].joints_angles, elem['last_frame'][frame_elem], joints_angles)
                        transform = convert_fix_rule(fix_rule, transform, joints_angles, bone_idx, total_quantity + elem['length'] - 1)
                        key_values.append(transform[idx])

                    total_quantity += elem['length']
                    
            fc.keyframe_points.foreach_set("co", key_values)

            fc.update()

        print('{} done'.format(bone_name))

    print('=================\nresult:\n{}\n=================\n'.format(res_message))
    


    """ armature_obj.rotation_euler[0] = math.radians(90)
    armature_obj.rotation_euler[2] = math.radians(90) """

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return {'FINISHED'}


class MergeAn(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import.anmerge"
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
    self.layout.operator(MergeAn.bl_idname,
                         text="AN Merge(.json)")


def register():
    bpy.utils.register_class(MergeAn)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(MergeAn)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
