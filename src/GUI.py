import PySimpleGUI as sg

from copy import deepcopy
import PIL
from PIL import Image
from send2trash import send2trash
from Parser import Parser
from pathlib import Path
import configparser

import glob, io, os, shutil, webbrowser, fileinput, sys

xSize = 1280
ySize = 800
files_list = []
vehicle = {}
wing_list = []
dynamic_controller_list = []
lut_list = []
prev_directory = ''


# vehicle = { file : {header : {key : value} } }


def aeroLayout():
    aero_tab_layout = [[
        sg.Frame(title='WING SELECTION', layout=[
            [sg.Text('Wing'), sg.Combo(wing_list, enable_events=True,
                                       readonly=True, key='wing_name', size=(20, 1),
                                       tooltip='Wing identifier. A car can have as many wings as necessary.')
             ], [sg.Button('Add Another Wing', key='add_wing', size=(13, 1)),
                 sg.Button('Delete Wing', key='delete_wing', size=(13, 1))]
        ]),
        sg.Frame(title='DYNAMIC CONTROLLER SELECTION', layout=[
            [sg.Text('Dynamic Controller'),
             sg.Combo(dynamic_controller_list, enable_events=True, readonly=True,
                      key='dynamic_controller', size=(27, 1),
                      tooltip='Active aero. Dynamically controls the inclination of a wing, relative to various telemetry factors')
             ], [sg.Button('Add Dynamic Controller', key='add_dynamic_controller', size=(20, 1)),
                 sg.Button('Delete Dynamic Controller', key='delete_dynamic_controller', size=(20, 1))]
        ])], [
        sg.Frame(title='WING ATTRIBUTES', layout=[
            [sg.Text('Wing Name'), sg.InputText(key='WING_NAME', size=(20, 1), enable_events=True,
                                                tooltip='name of the wing')],
            [sg.Text('Length'), sg.InputText(key='CHORD', size=(6, 1), enable_events=True,
                                             tooltip='length of the wing in meters')],
            [sg.Text('Width'), sg.InputText(key='SPAN', size=(6, 1), enable_events=True,
                                            tooltip='Width of the wing in meters. both help'
                                                    ' determine the frontal area of the wing. '
                                                    'Single unit is used to simplify '
                                                    'calculations.')],
            [sg.Text('Position (X, Y, Z)'), sg.InputText(key='POSITION', size=(20, 1), enable_events=True,
                                                         tooltip='position in x,y,z '
                                                                 'starting from the '
                                                                 'CoG')],
            [sg.Text('COE of Lift'), sg.Combo(lut_list, size=(25, 1),
                                              enable_events=True, readonly=True, key='LUT_AOA_CL',
                                              tooltip='Coefficient of Lift lookup table'),
             sg.Button('Edit', key='edit_LUT_AOA_CL')],
            [sg.Text('Height Aero Lift Multiplier'), sg.Combo(lut_list, enable_events=True, size=(25, 1),
                                                              readonly=True, key='LUT_GH_CL',
                                                              tooltip='Height aero lift multiplier '
                                                                      'lookup table'),
             sg.Button('Edit', key='edit_LUT_GH_CL')],
            [sg.Text('COE of Lift Multiplier'), sg.InputText(key='CL_GAIN', enable_events=True,
                                                             readonly=True, size=(15, 1),
                                                             tooltip='Coefficient of Lift multiplier '
                                                                     '(for easy fine tuning)')],
            [sg.Text('COE of Drag'), sg.Combo(lut_list, enable_events=True, readonly=True, size=(25, 1),
                                              key='LUT_AOA_CD',
                                              tooltip='Coefficient of drag lookup table'),
             sg.Button('Edit', key='edit_LUT_AOA_CD')],
            [sg.Text('Height Aero Drag Multiplier'), sg.Combo(lut_list, enable_events=True, readonly=True,
                                                              key='LUT_GH_CD', size=(25, 1),
                                                              tooltip='Height aero drag '
                                                                      'multiplier '
                                                                      'table'),
             sg.Button('Edit', key='edit_LUT_GH_CD')],
            [sg.Text('COE of Drag Multiplier'), sg.InputText(key='CD_GAIN', enable_events=True, readonly=True,
                                                             size=(15, 1),
                                                             tooltip='Coefficient of drag '
                                                                     'multiplier (for easy '
                                                                     'fine tuning)')],
            [sg.Text('Default Starting Angle (Deg°)'), sg.InputText(key='ANGLE', size=(6, 1), enable_events=True,
                                                                    tooltip='Default starting'
                                                                            ' wing angle '
                                                                            '(degrees)')]
        ]),
        sg.Frame(title='DYNAMIC CONTROLLER ATTRIBUTES', vertical_alignment='t', layout=[
            [sg.Text('Wing'), sg.InputText(key='WING', size=(5, 1), enable_events=True,
                                           tooltip='Wing currently selected')],
            [sg.Text('Combinator'), sg.Combo(['ADD', 'MULT'],
                                             default_value='ADD', enable_events=True, readonly=True,
                                             key='COMBINATOR', size=(10, 1),
                                             tooltip='COMBINATOR MODE: ADD or MULT')],
            [sg.Text('Input'), sg.Combo(['BRAKE', 'SPEED_KMH'],
                                        default_value='BRAKE', enable_events=True, readonly=True,
                                        key='INPUT', size=(13, 1),
                                        tooltip='Telemetry channel input. LONG LATG BRAKE0-1'
                                                ' GAS0-1 STEER-1+1 SPEED')],
            [sg.Text('Input Data'), sg.Combo(lut_list, enable_events=True, readonly=True,
                                             key='LUT', size=(15, 1),
                                             tooltip='Input data to wing angle '
                                                     'lookup table'),
             sg.Button('Edit', key='edit_LUT')],
            [sg.Text('Filter'), sg.InputText(key='FILTER', size=(10, 1), enable_events=True,
                                             tooltip='Movement filter. Controls speed of '
                                                     'wing movement from one angle to '
                                                     'another.')],
            [sg.Text('Up Limit'), sg.InputText(key='UP_LIMIT', size=(6, 1), enable_events=True,
                                               tooltip='Wing angle max limit')],
            [sg.Text('Down Limit'), sg.InputText(key='DOWN_LIMIT', size=(6, 1), enable_events=True,
                                                 tooltip='Wing angle min limit')]
        ])]
    ]
    return aero_tab_layout


def engineLayout():
    engine_tab_layout = [[
        sg.Frame(title='ENGINE', layout=[
            [sg.Text('Power Curve'),
             sg.Combo(lut_list, key='[HEADER]POWER_CURVE', size=(25, 1), enable_events=True,
                      tooltip='power curve file'),
             sg.Button('Edit', key='edit_[HEADER]POWER_CURVE')],
            [sg.Text('Coast Curve'),
             sg.Combo(['FROM_COAST_REF', 'FROM_COAST_DATA', 'FROM_COAST_CURVE'], default_value='FROM_COAST_REF',
                      key='[HEADER][COAST_CURVE]', size=(20, 1), enable_events=True,
                      tooltip='Can define 3 different options (coast reference, '
                              'coast values for mathematical curve, and coast curve file')]
        ]),
        sg.Frame(title='Coast Ref', layout=[
            [sg.Text('RPM'), sg.InputText(key='[COAST_REF]RPM', size=(10, 1), enable_events=True,
                                          tooltip='rev number reference')],
            [sg.Text('Torque'), sg.InputText(key='[COAST_REF]TORQUE', size=(10, 1), enable_events=True,
                                             tooltip='engine braking torque value in Nm at rev number reference')],
            [sg.Text('Non Linearity'), sg.InputText(key='[COAST_REF]NON_LINEARITY', size=(10, 1), enable_events=True,
                                                    tooltip='coast engine brake from ZERO to TORQUE value \n'
                                                            'at rpm with linear (0) to fully exponential (1)')]
        ])], [
        sg.Frame(title='Engine Data', layout=[
            [sg.Text('Altitude Sensitivity'), sg.InputText(key='[ENGINE_DATA]ALTITUDE_SENSITIVITY', size=(10, 1),
                                                           enable_events=True, tooltip='Sensitivity to altitude')],
            [sg.Text('Inertia'), sg.InputText(key='[ENGINE_DATA]INERTIA', size=(10, 1), enable_events=True,
                                              tooltip='engine inertia')],
            [sg.Text('Limiter'), sg.InputText(key='[ENGINE_DATA]LIMITER', size=(10, 1), enable_events=True,
                                              tooltip='engine rev limiter. 0 no limiter')],
            [sg.Text('Limiter Hz'), sg.InputText(key='[ENGINE_DATA]LIMITER_HZ', size=(10, 1), enable_events=True,
                                                 tooltip='Frequency of engine limiter')],
            [sg.Text('Idle RPM'), sg.InputText(key='[ENGINE_DATA]MINIMUM', size=(10, 1), enable_events=True,
                                               tooltip='Idle rpm')],
            [sg.Text('Default Turbo Adjustment'),
             sg.InputText(key='[ENGINE_DATA]DEFAULT_TURBO_ADJUSTMENT', size=(10, 1), enable_events=True,
                          tooltip='DEFAULT turbo adjustment if one or more turbos are cockpit adjustable')]
        ])], [
        sg.Frame(title='Turbo', layout=[
            [sg.Text('Lag Down'), sg.InputText(key='[TURBO_0]LAG_DN', size=(10, 1), enable_events=True,
                                               tooltip='Interpolation lag used slowing down the turbo')],
            [sg.Text('Lag Up'), sg.InputText(key='[TURBO_0]LAG_UP', size=(10, 1), enable_events=True,
                                             tooltip='Interpolation lag used to spin up the turbo')],
            [sg.Text('Max Boost'), sg.InputText(key='[TURBO_0]MAX_BOOST', size=(10, 1), enable_events=True,
                                                tooltip='Maximum boost generated. This value is never exceeded and \n'
                                                        'multiply the torque like T=T*(1.0 + boost), so a boost of 2 \n'
                                                        'will give you 3 times the torque at a given rpm.')],
            [sg.Text('WasteGate'), sg.InputText(key='[TURBO_0]WASTEGATE', size=(10, 1), enable_events=True,
                                                tooltip='Max level of boost before the wastegate does its things. 0 = '
                                                        'no wastegate')],
            [sg.Text('Display Max Boost'), sg.InputText(key='[TURBO_0]DISPLAY_MAX_BOOST', size=(10, 1),
                                                        enable_events=True,
                                                        tooltip='Value used by display apps')],
            [sg.Text('Reference Rpm'), sg.InputText(key='[TURBO_0]REFERENCE_RPM', size=(10, 1), enable_events=True,
                                                    tooltip='The reference rpm where the turbo reaches maximum boost '
                                                            '(at max gas pedal).')],
            [sg.Text('Gamma'), sg.InputText(key='[TURBO_0]GAMMA', size=(10, 1), enable_events=True,
                                            tooltip='Turbo pressure sensitivity on accelerator pedal')],
            [sg.Text('Cockpit Adjustable'), sg.InputText(key='[TURBO_0]COCKPIT_ADJUSTABLE', size=(10, 1),
                                                         enable_events=True,
                                                         tooltip='cockpit adjustable turbo pressure'),
             ]
        ])],
    ]
    return engine_tab_layout


def suspensionLayout():
    suspension_tab_layout = [
        [sg.Frame(title='SUSPENSION SELECTION', layout=[
            [sg.Text('Suspension Selection'),
             sg.Combo(['[FRONT]', '[REAR]'],
                      default_value='[FRONT]', readonly=True, key='suspension_location', size=(10, 1),
                      enable_events=True)]
        ])],
        [sg.Frame(title='Suspension', layout=[
            [sg.Text('Type'), sg.Combo(['DWB'], default_value='DWB', key='SUSPENSION_TYPE',
                                       size=(10, 1), enable_events=True, readonly=True,
                                       tooltip='Suspension type. DWB Double Wish Bones. STRUT McPherson strut'),
             sg.Text('Damp Fast Bump Threshold'), sg.InputText(key='DAMP_FAST_BUMPTHRESHOLD', size=(10, 1),
                                                               enable_events=True,
                                                               tooltip='Damper bump slow/fast threshold in seconds')],
            [sg.Text('Basey'), sg.InputText(key='BASEY', size=(10, 1), enable_events=True,
                                            tooltip='Distance of CG from the center of the wheel in meters. \n'
                                                    'Front Wheel Radius+BASEY=front CoG. \n'
                                                    'Actual CG height =(FWR+FBasey)+ (RWR+Rbasey))/CG_LOCATION%'),
             sg.Text('Damp Rebound'), sg.InputText(key='DAMP_REBOUND', size=(10, 1), enable_events=True,
                                                   tooltip='Damper wheel rate stiffness in N sec/m \n'
                                                           'in slow speed rebound')],
            [sg.Text('Track'), sg.InputText(key='TRACK', size=(10, 1), enable_events=True,
                                            tooltip='Track width in meters \n'
                                                    '(from pivot 3D placement of the 3d model of a wheel)'),
             sg.Text('Damp Fast Rebound'), sg.InputText(key='DAMP_FAST_REBOUND', size=(10, 1), enable_events=True,
                                                        tooltip='Damper wheel rate stiffness in N sec/m in fast speed '
                                                                'rebound')],
            [sg.Text('Rod Length'), sg.InputText(key='ROD_LENGTH', size=(10, 1), enable_events=True,
                                                 tooltip='push rod length in meters. positive raises ride height, \n'
                                                         'negative lowers ride height.'),
             sg.Text('Damp Fast Rebound Threshold'), sg.InputText(key='DAMP_FAST_REBOUNDTHRESHOLD', size=(10, 1),
                                                                  enable_events=True,
                                                                  tooltip='Damper rebound slow/fast threshold in '
                                                                          'seconds')],
            [sg.Text('Hub Mass'), sg.InputText(key='HUB_MASS', size=(10, 1), enable_events=True,
                                               tooltip='Front sprung mass'),
             sg.Text('Damp Bump'), sg.InputText(key='DAMP_BUMP', size=(10, 1), enable_events=True,
                                                tooltip='Damper wheel rate stiffness in N sec/m \n'
                                                        'in slow speed compression')],
            [sg.Text('Rim Offset'), sg.InputText(key='RIM_OFFSET', size=(10, 1), enable_events=True,
                                                 tooltip='Rim offset in meters'),
             sg.Text('Damp Fast Bump'), sg.InputText(key='DAMP_FAST_BUMP', size=(10, 1), enable_events=True,
                                                     tooltip='Damper wheel rate stiffness in N sec/m \n'
                                                             'in fast speed compression')],
            [sg.Text('Toe Out'), sg.InputText(key='TOE_OUT', size=(10, 1), enable_events=True,
                                              tooltip='Toe-out expressed as the \n'
                                                      'length of the steering arm in meters'),
             sg.Text('Bump Stop Rate'), sg.InputText(key='BUMP_STOP_RATE', size=(10, 1), enable_events=True,
                                                     tooltip='bump stop spring rate')],
            [sg.Text('Static Camber'), sg.InputText(key='STATIC_CAMBER', size=(10, 1), enable_events=True,
                                                    tooltip='Static Camber in degrees. Actual camber relative to \n'
                                                            'suspension geometry and movement, check values in game'),
             sg.Text('Bump Stop Up'), sg.InputText(key='BUMPSTOP_UP', size=(10, 1), enable_events=True,
                                                   tooltip='meters to upper bumpstop from the 0 design of the '
                                                           'suspension')],
            [sg.Text('Spring Rate'), sg.InputText(key='SPRING_RATE', size=(10, 1), enable_events=True,
                                                  tooltip='Wheel rate stiffness in Nm. \n'
                                                          'Do not use spring value but calculate wheel rate'),
             sg.Text('Bump Stop Down'), sg.InputText(key='BUMPSTOP_DN', size=(10, 1), enable_events=True,
                                                     tooltip='meters to bottom bumpstop \n'
                                                             'from the 0 design of the suspension')],
            [sg.Text('Progressive Spring Rate'), sg.InputText(key='PROGRESSIVE_SPRING_RATE', size=(10, 1),
                                                              enable_events=True,
                                                              tooltip='progressive spring rate in N/m/m'),
             sg.Text('Packer Range'), sg.InputText(key='PACKER_RANGE', size=(10, 1), enable_events=True,
                                                   tooltip='Total suspension movement range, before hitting packers')],
            [sg.Text('Wish Bone Tire Top'), sg.InputText(key='WBTYRE_TOP', size=(18, 1), enable_events=True,
                                                         tooltip='Top tyre side wishbone attach point'),
             sg.Text('Wish Bone Tire Bottom'), sg.InputText(key='WBTYRE_BOTTOM', size=(18, 1), enable_events=True,
                                                            tooltip='Bottom tyre side wishbone attach point')],
            [sg.Text('Wish Bone Car Steer'), sg.InputText(key='WBCAR_STEER', size=(18, 1), enable_events=True,
                                                          tooltip='Steering rod car side attach point'),
             sg.Text('Wish Bone Tire Steer'), sg.InputText(key='WBTYRE_STEER', size=(18, 1), enable_events=True,
                                                           tooltip='Steering rod tyre side attach point')],
            [sg.Text('Wish Bone Car Top Front'), sg.InputText(key='WBCAR_TOP_FRONT', size=(18, 1), enable_events=True,
                                                              tooltip='Top front car side wishbone attach point'),
             sg.Text('Wish Bone Car Top Rear'), sg.InputText(key='WBCAR_TOP_REAR', size=(18, 1), enable_events=True,
                                                             tooltip='Top rear car side wishbone attach point')],
            [sg.Text('Wish Bone Car Bottom Front'), sg.InputText(key='WBCAR_BOTTOM_FRONT', size=(18, 1),
                                                                 enable_events=True,
                                                                 tooltip='Bottom front car side wishbone attach point'),
             sg.Text('Wish Bone Car Bottom Rear'), sg.InputText(key='WBCAR_BOTTOM_REAR', size=(18, 1),
                                                                enable_events=True,
                                                                tooltip='Bottom rear car side wishbone attach point')],
        ])],
        [sg.Frame(title='Basic', layout=[
            [sg.Text('Wheelbase'), sg.InputText(key='WHEELBASE', size=(10, 1),
                                                tooltip='Wheelbase distance in meters')],
            [sg.Text('Center of Gravity Location'), sg.InputText(key='CG_LOCATION', size=(10, 1), enable_events=True,
                                                                 tooltip='Front Weight distribution in percentage')]
        ]),
         sg.Frame(title='ARB', layout=[
             [sg.Text('Front'), sg.InputText(key='FRONT', size=(10, 1), enable_events=True,
                                             tooltip='Front antiroll bar stiffness. in Nm')],
             [sg.Text('Rear'), sg.InputText(key='REAR', size=(10, 1), enable_events=True,
                                            tooltip='Rear antiroll bar stiffness. in Nm')],
         ])]
    ]
    return suspension_tab_layout


tire_list = []


def tiresLayout():
    tires_tab_layout = [[
        sg.Frame(title='TIRE SELECTION', layout=[
            [sg.Text('Compound Selection'), sg.Combo(tire_list,
                                                     key='tire_name', size=(15, 1), enable_events=True),
             sg.Text('Short Name'), sg.InputText(key='SHORT_NAME', size=(15, 1), enable_events=True),
             sg.Button('Add New Tire', key='add_tire', enable_events=True, size=(15, 1))
             ],
            [sg.Text('Tire Location'), sg.Combo(['Front', 'Rear'],
                                                default_value='Front', readonly=True, key='tire_location', size=(10, 1),
                                                enable_events=True),
             sg.Text('Thermal Selection'), sg.Combo(['Thermal_Front', 'Thermal_Rear'],
                                                    default_value='Thermal_Front', readonly=True,
                                                    key='thermal_location',
                                                    size=(20, 1), enable_events=True),
             sg.Button('Delete Tire', key='delete_tire', enable_events=True, size=(15, 1))
             ]
        ])
    ], [
        sg.Frame(title='TIRE ATTRIBUTES', layout=[
            [sg.Text('Tire Width'), sg.InputText(key='WIDTH', size=(6, 1), enable_events=True,
                                                 tooltip='Tyre width in meters'),
             sg.Text('Tire Radius'), sg.InputText(key='RADIUS', size=(6, 1), enable_events=True,
                                                  tooltip='Tyre radius in meters')],
            [sg.Text('Rim Radius'), sg.InputText(key='RIM_RADIUS', size=(6, 1), enable_events=True,
                                                 tooltip='rim radius in meters (use 1 inch more than nominal, \n'
                                                         'in this example 13inch rims must be calculated as 14inch)')],
            [sg.Text('Angular Inertia'), sg.InputText(key='ANGULAR_INERTIA', size=(6, 1), enable_events=True,
                                                      tooltip='angular inertia of front rim+tyre+brake disc together')],
            [sg.Text('Damping Rate'), sg.InputText(key='DAMP', size=(6, 1), enable_events=True,
                                                   tooltip='Damping rate of front tyre in N sec/m \n'
                                                           '(values usually from 200 to 1400)'),
             sg.Text('Spring Rate'), sg.InputText(key='RATE', size=(6, 1), enable_events=True,
                                                  tooltip='Spring rate of front tyres in Nm')],
            [sg.Text('DY0'), sg.InputText(key='DY0', size=(6, 1), enable_events=True,
                                          tooltip='DY0'),
             sg.Text('DY1'), sg.InputText(key='DY1', size=(6, 1), enable_events=True,
                                          tooltip='DY1')],
            [sg.Text('DX0'), sg.InputText(key='DX0', size=(6, 1), enable_events=True,
                                          tooltip='DX0'),
             sg.Text('DX1'), sg.InputText(key='DX1', size=(6, 1), enable_events=True,
                                          tooltip='DX1')],
            [sg.Text('Wear Curve'),
             sg.Combo(lut_list, key='WEAR_CURVE', size=(25, 1), readonly=True, enable_events=True,
                      tooltip='file with lookup table to call'),
             sg.Button('Edit', key='edit_WEAR_CURVE')],
            [sg.Text('Speed sensitivity value'), sg.InputText(key='SPEED_SENSITIVITY', size=(6, 1),
                                                              enable_events=True,
                                                              tooltip='speed sensitivity value')],
            [sg.Text('Relaxation Length'), sg.InputText(key='RELAXATION_LENGTH', size=(10, 1), enable_events=True,
                                                        tooltip='Relaxation length')],
            [sg.Text('Rolling Resistance Constant Component'), sg.InputText(key='ROLLING_RESISTANCE_0', size=(10, 1),
                                                                            enable_events=True,
                                                                            tooltip='rolling resistance constant '
                                                                                    'component')],
            [sg.Text('Rolling Resistance Velocity^2 Component'),
             sg.InputText(key='ROLLING_RESISTANCE_1', size=(10, 1), enable_events=True,
                          tooltip='rolling resistance velocity (squared) '
                                  'component')],
            [sg.Text('Rolling Resistance Slip angle Component'),
             sg.InputText(key='ROLLING_RESISTANCE_SLIP', size=(10, 1), enable_events=True,
                          tooltip='rolling reistance slip angle component')],
            [sg.Text('Tire Profile Flex'), sg.InputText(key='FLEX', size=(10, 1), enable_events=True,
                                                        tooltip='tire profile flex. the bigger the number the bigger \n'
                                                                'the flex, the bigger the added slip angle with load.')]
        ]),
        sg.Frame(title='TIRE ATTRIBUTES', layout=[
            [sg.Text('D Camber 0'), sg.InputText(key='DCAMBER_0', size=(6, 1), enable_events=True,
                                                 tooltip='DCAMBER 0'),
             sg.Text('Camber Gain'), sg.InputText(key='CAMBER_GAIN', size=(6, 1), enable_events=True,
                                                  tooltip='Camber gain value as slip angle multiplayer. default 1')],
            [sg.Text('D Camber 1'), sg.InputText(key='DCAMBER_1', size=(6, 1), enable_events=True,
                                                 tooltip='D dependency on camber. \n'
                                                         'D=D*(1.0 - (camberRAD*DCAMBER_0 + camberRAD^2 * DCAMBER_1))\n'
                                                         'camberRAD=absolute value of camber in radians')],
            [sg.Text('Friction limit angle'), sg.InputText(key='FRICTION_LIMIT_ANGLE', size=(6, 1),
                                                           enable_events=True,
                                                           tooltip='Friction limit angle')],
            [sg.Text('XMU'), sg.InputText(key='XMU', size=(6, 1), enable_events=True,
                                          tooltip='XMU')],
            [sg.Text('Static cold pressure'), sg.InputText(key='PRESSURE_STATIC', size=(6, 1), enable_events=True,
                                                           tooltip='STATIC (COLD) PRESSURE')],
            [sg.Text('Pressure Spring Gain'), sg.InputText(key='PRESSURE_SPRING_GAIN', size=(6, 1),
                                                           enable_events=True,
                                                           tooltip='INCREASE IN N/m  per psi (from 26psi reference)')],
            [sg.Text('Pressure Flex Gain'), sg.InputText(key='PRESSURE_FLEX_GAIN', size=(6, 1), enable_events=True,
                                                         tooltip='INCREASE IN FLEX per psi')],
            [sg.Text('Increase in RR resistance per PSI'), sg.InputText(key='PRESSURE_RR_GAIN', size=(6, 1),
                                                                        enable_events=True,
                                                                        tooltip='INCREASE IN RR RESISTENCE per psi')],
            [sg.Text('Loss of tire footprint with pressure rise'), sg.InputText(key='PRESSURE_D_GAIN', size=(6, 1),
                                                                                enable_events=True,
                                                                                tooltip='loss of tyre footprint with '
                                                                                        'pressure rise.')],
            [sg.Text('Ideal pressure for grip'), sg.InputText(key='PRESSURE_IDEAL', size=(6, 1), enable_events=True,
                                                              tooltip='Ideal pressure for grip')],
            [sg.Text('Flex Gain'), sg.InputText(key='FLEX_GAIN', size=(6, 1), enable_events=True,
                                                tooltip='Flex Gain'),
             sg.Text('FZ0'), sg.InputText(key='FZ0', size=(6, 1), enable_events=True,
                                          tooltip='FZ0')],
            [sg.Text('LS EXPY'), sg.InputText(key='LS_EXPY', size=(6, 1), enable_events=True,
                                              tooltip='LS EXPY'),
             sg.Text('LS EXPX'), sg.InputText(key='LS_EXPX', size=(6, 1), enable_events=True,
                                              tooltip='LS EXPX')],
            [sg.Text('DX REF'), sg.InputText(key='DX_REF', size=(6, 1), enable_events=True,
                                             tooltip='DX REF'),
             sg.Text('DY REF'), sg.InputText(key='DY_REF', size=(6, 1), enable_events=True,
                                             tooltip='DY REF')],
            [sg.Text('Fall Off Level'), sg.InputText(key='FALLOFF_LEVEL', size=(6, 1), enable_events=True,
                                                     tooltip='Falloff level'),
             sg.Text('Fall Off Speed'), sg.InputText(key='FALLOFF_SPEED', size=(6, 1), enable_events=True,
                                                     tooltip='Falloff speed')],
        ])
    ], [
        sg.Frame(title='THERMAL', layout=[
            [sg.Text('Surface Transfer'), sg.InputText(key='SURFACE_TRANSFER', size=(10, 1), enable_events=True,
                                                       tooltip='Surface transfer'),
             sg.Text('Patch Transfer'), sg.InputText(key='PATCH_TRANSFER', size=(10, 1), enable_events=True,
                                                     tooltip='Patch transfer'),
             sg.Text('Core Transfer'), sg.InputText(key='CORE_TRANSFER', size=(10, 1), enable_events=True,
                                                    tooltip='Core transfer')],
            [sg.Text('Internal Core Transfer'), sg.InputText(key='INTERNAL_CORE_TRANSFER', size=(10, 1),
                                                             enable_events=True,
                                                             tooltip='Internal core transfer'),
             sg.Text('Friction Temperature'), sg.InputText(key='FRICTION_K', size=(10, 1), enable_events=True,
                                                           tooltip='Friction temperature')],
            [sg.Text('Rolling Resistance Temperature'), sg.InputText(key='ROLLING_K', size=(10, 1),
                                                                     enable_events=True,
                                                                     tooltip='rolling resistance temp'),
             sg.Text('Cool Factor'), sg.InputText(key='COOL_FACTOR', size=(10, 1), enable_events=True,
                                                  tooltip='Cool factor')],
            [sg.Text('Temp/grip relation'), sg.Combo(lut_list, size=(25, 0), key='PERFORMANCE_CURVE',
                                                     readonly=True, enable_events=True,
                                                     tooltip='File to use for temperature/grip '
                                                             'relation'),
             sg.Button('Edit', key='edit_PERFORMANCE_CURVE'),
             sg.Text('Surfacing rolling temp'), sg.InputText(key='SURFACE_ROLLING_K', size=(10, 1),
                                                             enable_events=True,
                                                             tooltip='Surface rolling temperature')
             ],
            [sg.Text('Gamma Gamma'), sg.InputText(key='GRAIN_GAMMA', size=(10, 1), enable_events=True,
                                                  tooltip='Gamma for the curve grain vs slip. \n'
                                                          'higher number makes grain more influenced by slip'),
             sg.Text('Graining Grain'), sg.InputText(key='GRAIN_GAIN', size=(10, 1), enable_events=True,
                                                     tooltip='Gain for graining. How much gain raises with slip \n'
                                                             'and temperature difference - 100 value \n'
                                                             '= slipangle*(1+grain%)')],
            [sg.Text('Blister Gamma'), sg.InputText(key='BLISTER_GAMMA', size=(10, 1), enable_events=True,
                                                    tooltip='Gamma for the curve blistering vs slip. \n'
                                                            'higher number makes blistering more influenced by slip'),
             sg.Text('Blister Gain'), sg.InputText(key='BLISTER_GAIN', size=(10, 1), enable_events=True,
                                                   tooltip='Gain for blistering. How much blistering raises with slip\n'
                                                           'and temperature difference. think blistering more as heat\n'
                                                           'cycles. 100 value = 20% less grip')],
        ])
    ]]
    return tires_tab_layout


def ratiosLayout():
    ratios_tab_layout = [[
        sg.Frame(title='', layout=[[
            sg.Text('Number of forward gears'),
            sg.Combo([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                     default_value=0, enable_events=True, readonly=True, key='[GEARS]COUNT')]
        ])
    ]]

    # a layout of a column of a layout
    reverse_gear_column = sg.Column([[sg.Text('Reverse'), sg.InputText(key='[GEARS]GEAR_R', enable_events=True,
                                                                       tooltip='rear gear ratio')]],
                                    key='reverse_gear', visible=False)
    ratios_tab_layout.append([reverse_gear_column])

    i = 1
    while i < 11:
        ratios_tab_layout.append([sg.Column([[
            sg.Text(i), sg.InputText(key='[GEARS]GEAR_' + str(i), enable_events=True, tooltip='gear ' + str(i) + ' ratio')]],
            key=str(i) + '_gear', visible=False)])
        i += 1
    ratios_tab_layout.append([sg.Column([[
        sg.Text('Final'), sg.InputText(key='[GEARS]FINAL', enable_events=True, tooltip='final gear ratio')]],
        key='final_gear', visible=False)])
    return ratios_tab_layout


def brakesLayout():
    brakes_tab_layout = [[
        sg.Frame(title='MAX TORQUE', layout=[
            [sg.Text('Maximum braking force in Nm'), sg.InputText(key='[DATA]MAX_TORQUE', size=(10, 1),
                                                                  enable_events=True,
                                                                  tooltip='Maximum Brake torque in Nm')]
        ])], [
        sg.Frame(title='FRONT SHARE', layout=[
            [sg.Text('Changes the bias of the brakes with a percentage at the front axis'),
             sg.InputText(key='[DATA]FRONT_SHARE', size=(10, 1), enable_events=True,
                          tooltip='Percentage of brake torque at front axis')]
        ])], [
        sg.Frame(title='HAND BRAKE TORQUE', layout=[
            [sg.Text('Force of the handbrake at the rear wheel in Nm'),
             sg.InputText(key='[DATA]HANDBRAKE_TORQUE', size=(10, 1), enable_events=True,
                          tooltip='Handbrake torque (at the rear wheels)')]
        ])], [
        sg.Frame(title='COCKPIT ADJUSTABLE', layout=[
            [sg.Text('Changes the bias of the brakes with a percentage at the front axis'),
             sg.InputText(key='[DATA]COCKPIT_ADJUSTABLE', size=(10, 1), enable_events=True,
                          tooltip='0: no bias control from cockpit, 1: bias control from cockpit')]
        ])], [
        sg.Frame(title='ADJUST STEP', layout=[
            [sg.Text('Changes the bias of the brakes with a percentage at the front axis'),
             sg.InputText(key='[DATA]ADJUST_STEP', size=(10, 1), enable_events=True,
                          tooltip='step for bias cockpit adjustment.')]
        ])]
    ]
    return brakes_tab_layout


def drivetrainLayout():
    drivetrain_tab_layout = [[
        sg.Frame(title='TYPE', layout=[
            [sg.Text('Type'), sg.Combo(['AWD', 'FWD', 'RWD'],
                                       readonly=True, key='[TRACTION]TYPE', size=(10, 1),
                                       enable_events=True,
                                       tooltip='Wheel drive. Possible options: \n'
                                               'FWD (Front Wheel Drive), RWD (Rear Wheel Drive)\n'
                                                'AWD (All Wheel Drive)')]
        ]), sg.Frame(title='CLUTCH', layout=[
            [sg.Text('Max torque'), sg.InputText(key='[CLUTCH]MAX_TORQUE', size=(10, 1), enable_events=True,
                                                 tooltip='Max torque')]
        ]), sg.Frame(title='DAMAGE', layout=[
            [sg.Text('RPM damage window'), sg.InputText(key='[DAMAGE]RPM_WINDOW_K', size=(10, 1), enable_events=True,
                                                        tooltip='RPM damage window')]
        ])
    ], [
        sg.Frame(title='GEARBOX', layout=[
            [sg.Text('Gear change up time'), sg.InputText(key='[GEARBOX]CHANGE_UP_TIME', size=(10, 1),
                                                          enable_events=True,
                                                          tooltip='change up time in milliseconds')],
            [sg.Text('Gear change down time'), sg.InputText(key='[GEARBOX]CHANGE_DN_TIME', size=(10, 1),
                                                            enable_events=True,
                                                            tooltip='change down time in milliseconds')],
            [sg.Text('Auto cutoff time for upshifts'),
             sg.InputText(key='[GEARBOX]AUTO_CUTOFF_TIME', size=(10, 1), enable_events=True,
                          tooltip='Auto cutoff time for upshifts in milliseconds')],
            [sg.Text('Shifter support?'),
             sg.InputText(key='[GEARBOX]SUPPORTS_SHIFTER', size=(10, 1), enable_events=True,
                          tooltip='1=Car supports shifter, 0=car supports only paddles')],
            [sg.Text('Valid shift rpm range window'),
             sg.InputText(key='[GEARBOX]VALID_SHIFT_RPM_WINDOW', size=(10, 1), enable_events=True,
                          tooltip='range window additional to the \n'
                                  'precise rev matching rpm that permits gear engage.')],
            [sg.Text('Gear engagement pedal difficulty multiplier'),
             sg.InputText(key='[GEARBOX]CONTROLS_WINDOW_GAIN', size=(10, 1), enable_events=True,
                          tooltip='multiplayer for gas,brake,clutch pedals \n'
                                  'that permits gear engage on different rev \n'
                                  'matching rpm. the lower the more difficult.')],
            [sg.Text('Gearbox inertia'), sg.InputText(default_text='0.02', key='[GEARBOX]INERTIA', size=(10, 1),
                                                      enable_events=True,
                                                      tooltip='gearbox inertia. default values to 0.02 if not set')]
        ]),
        sg.Frame(title='DIFFERENTIAL', layout=[
            [sg.Text('Diff lock under power'), sg.InputText(key='[DIFFERENTIAL]POWER', size=(10, 1),
                                                            enable_events=True,
                                                            tooltip='differential lock under power. 1.0=100% lock - 0 '
                                                                    '0% lock')],
            [sg.Text('Diff lock when coasting'), sg.InputText(key='[DIFFERENTIAL]COAST', size=(10, 1),
                                                              enable_events=True,
                                                              tooltip='differential lock under coasting. 1.0=100% lock '
                                                                      '0=0% lock')],
            [sg.Text('Diff preload torque setting'),
             sg.InputText(key='[DIFFERENTIAL]PRELOAD', size=(10, 1), enable_events=True,
                          tooltip='preload torque setting')]
        ])
    ], [
        sg.Frame(title='AUTOCLUTCH', layout=[
            [sg.Text('Upshift profile'), sg.Combo(['None'],
                                                  default_value='None', readonly=True,
                                                  key='[AUTOCLUTCH]UPSHIFT_PROFILE', size=(25, 1),
                                                  enable_events=True,
                                                  tooltip='Name of the autoclutch profile for upshifts. \n'
                                                          'NONE to disable autoclutch on shift up')],
            [sg.Text('Downshift profile'), sg.Combo(['None', 'DOWNSHIFT_PROFILE'],
                                                    default_value='None', readonly=True,
                                                    key='[AUTOCLUTCH]DOWNSHIFT_PROFILE', size=(25, 1),
                                                    enable_events=True,
                                                    tooltip='Name of the autoclutch profile for downshifts \n'
                                                            'NONE to disable autoclutch on shift down')],
            [sg.Text('Use autoclutch on gear shifts'), sg.Combo(['0', '1'],
                                                                readonly=True, key='[AUTOCLUTCH]USE_ON_CHANGES',
                                                                size=(10, 1), enable_events=True,
                                                                tooltip='Use the autoclutch on gear shifts even when \n'
                                                                        'autoclutch is set to off. Needed for \n'
                                                                        'cars with semiautomatic gearboxes. '
                                                                        'values 1,0')],
            [sg.Text('Minimum rpm for autoclutch engagement'), sg.InputText(key='[AUTOCLUTCH]MIN_RPM', size=(10, 1),
                                                                            enable_events=True,
                                                                            tooltip='Minimum rpm for autoclutch '
                                                                                    'engagement')],
            [sg.Text('Maximum rpm for autoclutch engagement'), sg.InputText(key='[AUTOCLUTCH]MAX_RPM', size=(10, 1),
                                                                            enable_events=True,
                                                                            tooltip='Maximum rpm for autoclutch '
                                                                                    'engagement')]
        ]),
        sg.Frame(title='AUTOBLIP', layout=[
            [sg.Text('Electronic'), sg.InputText(key='[AUTOBLIP]ELECTRONIC', size=(10, 1), enable_events=True,
                                                 tooltip='If = 1 then it is a feature of the car \n'
                                                         'and cannot be disabled')],
            [sg.Text('Time to reach full level'), sg.InputText(key='[AUTOBLIP]POINT_0', size=(10, 1),
                                                               enable_events=True,
                                                               tooltip='Time to reach full level')],
            [sg.Text('Time to start releasing gas'), sg.InputText(key='[AUTOBLIP]POINT_1', size=(10, 1),
                                                                  enable_events=True,
                                                                  tooltip='Time to start releasing gas')],
            [sg.Text('Time to reach 0 gas'), sg.InputText(key='[AUTOBLIP]POINT_2', size=(10, 1), enable_events=True,
                                                          tooltip='Time to reach 0 gas')],
            [sg.Text('Gas level to be reached'), sg.InputText(key='[AUTOBLIP]LEVEL', size=(10, 1), enable_events=True,
                                                              tooltip='Gas level to be reached')],
        ])
    ], [
        sg.Frame(title='DOWNSHIFT PROFILE', layout=[
            [sg.Text('Time to reach fully depressed clutch'),
             sg.InputText(key='[DOWNSHIFT_PROFILE]POINT_0', size=(10, 1), enable_events=True,
                          tooltip='Time to reach fully depress clutch')],
            [sg.Text('Time to start releasing clutch'), sg.InputText(key='[DOWNSHIFT_PROFILE]POINT_1', size=(10, 1),
                                                                     enable_events=True,
                                                                     tooltip='Time to start releasing clutch')],
            [sg.Text('Time to reach fully released clutch'),
             sg.InputText(key='[DOWNSHIFT_PROFILE]POINT_2', size=(10, 1), enable_events=True,
                          tooltip='Time to reach fully released clutch')],
        ]),
        sg.Frame(title='AUTOSHIFTER', layout=[
            [sg.Text('RPM to auto upshift'), sg.InputText(key='[AUTO_SHIFTER]UP', size=(10, 1), enable_events=True,
                                                          tooltip='RPM to auto upshift')],
            [sg.Text('RPM to auto downshift'), sg.InputText(key='[AUTO_SHIFTER]DOWN', size=(10, 1),
                                                            enable_events=True,
                                                            tooltip='RPM to auto downshift')],
            [sg.Text('Slip threshold'),
             sg.InputText(default_text='1.1', key='[AUTO_SHIFTER]SLIP_THRESHOLD', size=(10, 1), enable_events=True,
                          tooltip='Slip threshold')],
            [sg.Text('Gas cutoff time'),
             sg.InputText(default_text='0.28', key='[AUTO_SHIFTER]GAS_CUTOFF_TIME', size=(10, 1), enable_events=True,
                          tooltip='Gas cutoff time')]
        ])
    ]]
    return drivetrain_tab_layout


def carLayout():
    car_tab_layout = [[
        sg.Frame(title='BASIC', layout=[
            [sg.Text('Graphics Offset'), sg.InputText(key='[BASIC]GRAPHICS_OFFSET', size=(15, 1), enable_events=True,
                                                      tooltip='3 axis correction (x,y,z), \n'
                                                              'applies only to the 3D object of the car (meters)')],
            [sg.Text('Graphics Pitch Rotation'), sg.InputText(key='[BASIC]GRAPHICS_PITCH_ROTATION',
                                                              size=(10, 1), enable_events=True,
                                                              tooltip='Changes 3D object rotation in pitch (degrees)')],
            [sg.Text('Vehicle Weight'), sg.InputText(key='[BASIC]TOTALMASS', size=(10, 1), enable_events=True,
                                                     tooltip='Total vehicle weight in kg with driver and no fuel')],
            [sg.Text('Polar Inertia'), sg.InputText(key='[BASIC]INERTIA', size=(10, 1), enable_events=True,
                                                    tooltip='Car polar inertia. Calculated from the car dimensions. \n'
                                                            'Start with the generic width,height,length and modify \n'
                                                            'accordingly to the car\'s configuration')]
        ]),
        sg.Frame(title='RIDE HEIGHT', layout=[
            [sg.Text('Front Ride Height Pickup'), sg.InputText(key='[RIDE]PICKUP_FRONT_HEIGHT',
                                                               size=(10, 1), enable_events=True,
                                                               tooltip='Height of the front ride height \n'
                                                                       'pickup point in meters WRT cg')],
            [sg.Text('Rear Ride Height Pickup'), sg.InputText(key='[RIDE]PICKUP_REAR_HEIGHT',
                                                              size=(10, 1), enable_events=True,
                                                              tooltip='Height of the rear ride height \n'
                                                                      'pickup point in meters WRT cg')],
            [sg.Text('Minimum Height Rule'), sg.InputText(key='[RULES]MIN_HEIGHT', size=(10, 1), enable_events=True,
                                                          tooltip='meters minimum height rule front/rear')],
        ])
    ], [
        sg.Frame(title='CONTROLS', layout=[
            [sg.Text('Force feedback multiplier'), sg.InputText(key='[CONTROLS]FFMULT', size=(10, 1),
                                                                enable_events=True,
                                                                tooltip='Forced Feedback Multiplier')],
            [sg.Text('Steering Assist'), sg.InputText(key='[CONTROLS]STEER_ASSIST', size=(10, 1), enable_events=True,
                                                      tooltip='Steering Assist')],
            [sg.Text('Steering Lock'), sg.InputText(key='[CONTROLS]STEER_LOCK', size=(10, 1), enable_events=True,
                                                    tooltip='Real car\'s steer lock from center to right')],
            [sg.Text('Steering Ratio'), sg.InputText(key='[CONTROLS]STEER_RATIO', size=(10, 1), enable_events=True,
                                                     tooltip='Steering Ratio')],
            [sg.Text('Linear Steer Rod Ratio'), sg.InputText(key='[CONTROLS]LINEAR_STEER_ROD_RATIO',
                                                             size=(10, 1), enable_events=True,
                                                             tooltip='Steps to manually calculate the steer rod ratio:'
                                                                     'Enter AC in dev app mode enabled \n'
                                                                     'Open SUSPENSIONS app \n'
                                                                     'turn your steering wheel by 90 degrees \n'
                                                                     'check the actual steer ratio value \n'
                                                                     'modify LINEAR_STEER_ROD_RATIO value until \n'
                                                                     'ingame steer ratio and car.ini STEER_RATIO \n'
                                                                     'values are similar')]
        ]),
        sg.Frame(title='FUEL', layout=[
            [sg.Text('Fuel Consumption'), sg.InputText(key='[FUEL]CONSUMPTION', size=(10, 1), enable_events=True,
                                                       tooltip='fuel consumption. In one second the consumption is \n'
                                                               '(rpm*gas*CONSUMPTION)/1000 litres')],
            [sg.Text('Starting Fuel Capacity'), sg.InputText(key='[FUEL]FUEL', size=(10, 1), enable_events=True,
                                                             tooltip='default starting fuel in litres')],
            [sg.Text('Max Fuel Capacity'), sg.InputText(key='[FUEL]MAX_FUEL', size=(10, 1), enable_events=True,
                                                        tooltip='max fuel in litres')],
            [sg.Text('Position of fuel tank'), sg.InputText(key='[FUELTANK]POSITION', size=(10, 1), enable_events=True,
                                                            tooltip='Position of fuel tank from CoG in meters')]
        ]),
    ], [
        sg.Frame(title='PIT STOP', layout=[
            [sg.Text('Time Spent to Change Each Tire'),
             sg.InputText(key='[PIT_STOP]TYRE_CHANGE_TIME_SEC', size=(10, 1), enable_events=True,
                          tooltip='time spent to change each tyre')],
            [sg.Text('Time Spent To Fuel Up 1 Liter of Fuel'),
             sg.InputText(key='[PIT_STOP]FUEL_LITER_TIME_SEC', size=(10, 1), enable_events=True,
                          tooltip='time spent to put 1 lt of fuel inside the car')],
            [sg.Text('Time Spent To Repair 10% of Body Damage'),
             sg.InputText(key='[PIT_STOP]BODY_REPAIR_TIME_SEC', size=(10, 1), enable_events=True,
                          tooltip='time spent to repair 10% of body damage')],
            [sg.Text('Time Spent To Repair 10% of Engine Damage'),
             sg.InputText(key='[PIT_STOP]ENGINE_REPAIR_TIME_SEC', size=(10, 1), enable_events=True,
                          tooltip='time spent to repair 10% of engine damage')],
            [sg.Text('Time Spent To Repair 10% of Suspension Damage'),
             sg.InputText(key='[PIT_STOP]SUSP_REPAIR_TIME_SEC', size=(10, 1), enable_events=True,
                          tooltip='time spent to repair 10% of suspension damage')],
        ])
    ]]
    return car_tab_layout


def windowSetup():
    # The TabGroup layout - it must contain only Tabs
    tab_group_layout = [[sg.Tab('Aero', aeroLayout(), key='aero'),
                         sg.Tab('Engine', engineLayout(), key='engine'),
                         sg.Tab('Suspension', suspensionLayout(), key='suspension'),
                         sg.Tab('Tires', tiresLayout(), key='tyres'),
                         sg.Tab('Ratios', ratiosLayout(), key='ratios'),
                         sg.Tab('Brakes', brakesLayout(), key='brakes'),
                         sg.Tab('Drivetrain', drivetrainLayout(), key='drivetrain'),
                         sg.Tab('Car', carLayout(), key='car')]]
    return tab_group_layout


def createWindowLayout():
    buttons = [[sg.Image('Default Files/preview_small.png', size=(240, 120), key='preview_image', visible=False)],
               [sg.Text(2*'                                              ',
                        key='car_name', font=40), sg.Button(button_text='edit', key='edit_name', visible=False)],
               [sg.Frame(title='', layout=[
                   [sg.Button('Electric Converter', size=(20, 0), key='ECC'),
                    sg.Button(button_text='edit', key='edit_ecc')],
                   [sg.Button('IC Converter', size=(20, 0), key='ICC'),
                    sg.Button(button_text='edit', key='edit_icc')]
               ], key='converters_frame', pad=((5, 0), (ySize - 400, 0)), visible=False)],
               [sg.FolderBrowse('Browse Cars', key='car_path', enable_events=True, size=(50, 20), pad=((5, 0), (40, 10))),
                sg.Ok(key='ok_1', size=(10, 3), pad=((5, 0), (40, 10)))],
               [sg.Text(2*'                                              ',
                        key='current_dir', pad=((0, 20), (0, 0)))]]

    buttons2 = [[sg.TabGroup(windowSetup(), enable_events=True, key='TABGROUP', border_width=10)],
                [sg.Button('Delete Car', key='delete_all', size=(9, 0), pad=((xSize - 765, 0), (0, 0))),
                 sg.Button('Save', size=(9, 0), key='save_all')],
                [sg.Text(2*'                                             ',
                        pad=((xSize - 675, 0), (0, 0)), key='new_dir')]]

    # All the stuff inside your window
    layout = [[sg.Column(buttons, justification='l', pad=((0, 100), (0, 0))),
               sg.Column(buttons2, visible=False, key='buttons2')]]
    return layout


# can probably separate this into multiple methods
# check buttons for window updates
# check values to update GUI
def runLoop():
    global prev_directory
    global files_list
    global vehicle
    values_set = False
    actual_name = ''
    name = ''
    wing = ''
    dynamic_controller = ''
    tires = ''
    tires_location = ''
    thermal_location = ''
    suspension = ''
    drive_type = ''
    ecc_max_torque = 1600
    ecc_max_rpm = 16000
    icc_max_rpm = 6500
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()
        directory = values['car_path']

        if event == sg.WIN_CLOSED or event == 'Cancel':
            break

        # if a car is selected
        if directory != '':
            window.Element('buttons2').Update(visible=True)
            directory += '/'
            # prev_directory = directory

            # changes directory if name has changed
            if actual_name != '' and actual_name != os.path.basename(os.path.dirname(os.path.dirname(directory))):
                directory = directory.replace(os.path.basename(os.path.dirname(os.path.dirname(directory))),
                                              actual_name)

            # reset if new directory
            # if prev_directory != '' and directory != prev_directory:
            if prev_directory != '' and values['car_path'] != prev_directory:
                files_list = []
                vehicle = {}
                values_set = False
                actual_name = ''
                name = ''
                wing = ''
                dynamic_controller = ''
                tires = ''
                tires_location = ''
                thermal_location = ''
                suspension = ''
                drive_type = ''
                ecc_max_torque = 140
                ecc_max_rpm = 20000

            window.Element('current_dir').Update(value=directory)
            prev_directory = values['car_path']

            # set values to be displayed
            # if not values_set or directory != prev_directory:
            if not values_set:
                try:
                    setValues(directory)
                    # setPreviewImage(directory)
                except FileNotFoundError as e:
                    window.Element('buttons2').Update(visible=False)
                    window.Element('car_name').Update(value='')
                    window.Element('edit_name').Update(visible=False)
                    directory = ''
                    window.Element('current_dir').Update(value=directory)
                    sg.popup_ok(
                        str(e) + '\n' + '*Make sure you are selecting the \"data\" folder of the desired vehicle')
                    continue

                updateInitialButtons()
                setPreviewImage(directory)
                # setValues(directory)
                wing = wing_list[0]
                if len(dynamic_controller_list) > 1:
                    dynamic_controller = dynamic_controller_list[0]
                else:
                    window.Element('delete_dynamic_controller').Update(disabled=True)
                if len(tire_list) < 2:
                    window.Element('delete_tire').Update(disabled=True)
                tires = values['tire_name']
                tires_location = 'Front'
                thermal_location = 'Thermal_Front'
                suspension = values['suspension_location']
                name = os.path.basename(os.path.dirname(os.path.dirname(directory)))
                window.Element('car_name').Update(value=name)
                values_set = True
                updateLUTList()
            else:
                file = getFile(values)
                # AERO
                if wing != values['wing_name']:  # updates wing
                    wing = values['wing_name']
                    updateTab(file, wing)
                elif dynamic_controller != values['dynamic_controller']:  # updates dynamic controller
                    dynamic_controller = values['dynamic_controller']
                    updateTab(file, dynamic_controller)
                # TIRES
                elif tires != values['tire_name']:  # updates tires
                    tires = values['tire_name']
                    tires_location = 'Front'
                    thermal_location = 'Thermal_Front'
                    window.Element('tire_location').Update(value=tires_location)
                    window.Element('thermal_location').Update(value=thermal_location)
                    updateTab(file, getHeader(tires, tires_location))
                    updateTab(file, getHeader(tires, thermal_location))
                elif tires_location != values['tire_location']:  # updates tire location
                    tires_location = values['tire_location']
                    updateTab(file, getHeader(tires, tires_location))
                elif thermal_location != values['thermal_location']:  # updates thermal location
                    thermal_location = values['thermal_location']
                    updateTab(file, getHeader(tires, thermal_location))
                # SUSPENSION
                elif suspension != values['suspension_location']:  # updates suspension
                    suspension = values['suspension_location']
                    updateTab(file, suspension)
                # DRIVETRAIN
                elif drive_type != values['[TRACTION]TYPE']:
                    if drive_type != '':
                        updateDriveType(file, values['[TRACTION]TYPE'], drive_type)
                    drive_type = values['[TRACTION]TYPE']
                else:  # updates window edits to dictionary
                    if file.__contains__('aero'):
                        wing = values['wing_name']
                        if dynamic_controller != '':
                            updateWindow(file, [wing, dynamic_controller], values)
                        else:
                            updateWindow(file, [wing], values)
                    elif file.__contains__('tyres'):
                        updateWindow(file, [getHeader(tires, tires_location),
                                            getHeader(tires, thermal_location)], values)
                    elif file.__contains__('suspension'):
                        updateWindow(file, [suspension], values)
                    else:
                        updateWindows(file, values)

            # update visibility of lut buttons
            # check if luck button was pressed
            updateLUTButtons(values)
            lutCheck(event, directory, values)

            updateRatios(values)
            window.Element('car_name').Update(value=name)

            if wing == '[WING_0]':
                window.Element('delete_wing').Update(disabled=True)
            if wing != '[WING_0]':
                window.Element('delete_wing').Update(disabled=False)

            if event == 'add_wing':
                addWing(directory, values['LUT_AOA_CL'], values['LUT_GH_CL'], values['LUT_AOA_CD'], values['LUT_GH_CD'])
            if event == 'delete_wing':
                if sg.popup_yes_no('Delete wing?') == 'Yes':
                    deleteWing(values['wing_name'])
            if event == 'add_dynamic_controller':
                addDynamicController(values)
            if event == 'delete_dynamic_controller' and values['dynamic_controller'] != '':
                if sg.popup_yes_no('Delete dynamic controller?') == 'Yes':
                    deleteDynamicController(values['dynamic_controller'])
                    if len(dynamic_controller_list) > 1:
                        dynamic_controller = dynamic_controller_list[0]
                    else:
                        dynamic_controller = ''

            if event == 'add_tire':
                addTire(directory, values['WEAR_CURVE'], values['PERFORMANCE_CURVE'])
                updateLUTButtons(values)

            if event == 'delete_tire':
                if sg.popup_yes_no('Delete tire?') == 'Yes':
                    deleteTire(tires)
                    tires = tire_list[0]
                    tires_location = 'Front'
                    thermal_location = 'Thermal_Front'

            if event == 'edit_ecc':
                ecc_max_torque = sg.popup_get_text(message='Max Torque Value', title='MAX TORQUE')
                ecc_max_rpm = sg.popup_get_text(message='Max RPM Value', title='MAX RPM')

            if event == 'edit_icc':
                icc_max_rpm = sg.popup_get_text(message='Max RPM Value', title='MAX RPM')

            if event == 'ECC':
                electricCarConversion(directory, ecc_max_torque, ecc_max_rpm)

            if event == 'ICC':
                internalCombustionCarConversion(directory, icc_max_rpm)

            if event == 'edit_name':
                input = sg.popup_get_text('Input vehicle name:',
                                          default_text=name)
                if input and not input.isspace() and input != os.path.basename(
                        os.path.dirname(os.path.dirname(directory))):
                    window.Element('car_name').Update(value=input)
                    name = input

            if event == 'save_all':
                try:
                    path = Path(os.path.dirname(os.path.dirname(directory)))
                    path.rename(path)
                except PermissionError as e:
                    sg.popup_ok(str(e) + '\n' +
                                '*Files in directory must be closed in all other programs before saving')
                    continue

                writeValues(values, prev_directory + '/', directory)
                prev_name = os.path.basename(os.path.dirname(os.path.dirname(directory)))
                # folder name
                if name != prev_name:
                    shutil.move(os.path.dirname(os.path.dirname(directory)),
                                os.path.dirname(os.path.dirname(os.path.dirname(directory))) + "/" + name)

                    # ui_car name
                    for line in fileinput.FileInput(
                            os.path.dirname(os.path.dirname(os.path.dirname(directory))) + "/" +
                            name + "/ui/ui_car.json", inplace=True):
                        if "\"name\":" in line:
                            line = "	\"name\": \"" + name + "\",\n"
                        sys.stdout.write(line)

                    # bank file
                    if prev_name.__contains__(' - Copy'):
                        shutil.move(os.path.dirname(os.path.dirname(os.path.dirname(directory))) + '/' + name + '/sfx/'
                                    + prev_name.replace(' - Copy', '') + '.bank',
                                    os.path.dirname(os.path.dirname(os.path.dirname(directory))) + '/'
                                    + name + '/sfx/' + name + '.bank')
                    else:
                        shutil.move(os.path.dirname(os.path.dirname(os.path.dirname(directory))) + '/' + name + '/sfx/'
                                    + prev_name + '.bank',
                                    os.path.dirname(os.path.dirname(os.path.dirname(directory))) + '/'
                                    + name + '/sfx/' + name + '.bank')

                    actual_name = name
                sg.popup_ok('Save successful')

            if event == 'delete_all':
                confirm = sg.popup_yes_no('Are you sure you want to delete \'' +
                                          os.path.basename(
                                              os.path.dirname(os.path.dirname(directory))) + '\' and all its contents?')
                if confirm == 'Yes':
                    send2trash(os.path.normpath(os.path.dirname(os.path.dirname(directory))))
                    window.Element("buttons2").Update(visible=False)
                    values_set = False


def updateInitialButtons():
    window.Element('car_path').set_size(size=(10, 0))
    window.Element('ok_1').set_size(size=(2, 0))
    window.Element('edit_name').Update(visible=True)
    window.Element('converters_frame').Update(visible=True)


def internalCombustionCarConversion(directory, max_rpm):
    rpm = int(max_rpm)   # default: 6500
    # update gear count
    window.Element('[GEARS]COUNT').Update(value=6)
    vehicle[files_list[5]]['[GEARS]']['COUNT'] = 6
    # update 1st gear ratio
    window.Element('[GEARS]GEAR_1').Update(value=2.36)
    vehicle[files_list[5]]['[GEARS]']['GEAR_1'] = 2.36
    # update 2nd gear ratio
    window.Element('[GEARS]GEAR_2').Update(value=1.73)
    vehicle[files_list[5]]['[GEARS]']['GEAR_2'] = 1.73
    # update 3rd gear ratio
    window.Element('[GEARS]GEAR_3').Update(value=1.4)
    vehicle[files_list[5]]['[GEARS]']['GEAR_3'] = 1.4
    # update 4th gear ratio
    window.Element('[GEARS]GEAR_4').Update(value=1.17)
    vehicle[files_list[5]]['[GEARS]']['GEAR_4'] = 1.17
    # update 5th gear ratio
    window.Element('[GEARS]GEAR_5').Update(value=1.00)
    vehicle[files_list[5]]['[GEARS]']['GEAR_5'] = 1.00
    # update 6th gear ratio
    window.Element('[GEARS]GEAR_6').Update(value=0.88)
    vehicle[files_list[5]]['[GEARS]']['GEAR_6'] = 0.88
    # update final gear ratio
    window.Element('[GEARS]FINAL').Update(value=3.10)
    vehicle[files_list[5]]['[GEARS]']['FINAL'] = 3.10
    # update rpm limiter
    window.Element('[ENGINE_DATA]LIMITER').Update(value=rpm)
    vehicle[files_list[1]]['[ENGINE_DATA]']['LIMITER'] = rpm
    # update coast_ref rpm
    window.Element('[COAST_REF]RPM').Update(value=rpm + 500)
    vehicle[files_list[1]]['[COAST_REF]']['RPM'] = rpm + 500
    # reference power.lut
    window.Element('[HEADER]POWER_CURVE').Update(value='power.lut')
    vehicle[files_list[1]]['[HEADER]']['POWER_CURVE'] = 'power.lut'

    #remove ers.ini if exists
    if os.path.exists(directory + '\ers.ini'):
        os.remove(directory + '\ers.ini')


def electricCarConversion(directory, max_torque, max_rpm):
    rpm = int(max_rpm)   # default: 21000
    torque = int(max_torque)    # default: 1600
    ers_file = 'ers.ini'
    ctrl_ers_file = 'ctrl_ers_0.ini'
    ev_power_file_name = 'electric_power.lut'
    ev_torque_file_name = 'kers_torque.lut'
    ev_coast_file_name = 'kers_torque_coast.lut'
    ev_gas_file_name = 'kers_gas.lut'
    ev_gear_file_name = 'kers_gear.lut'
    ev_slipratio_file_name = 'kers_slipratio.lut'

    # remove gears from 2 to gear count
    i = 2
    while i < int(vehicle[files_list[5]]['[GEARS]']['COUNT']):
        vehicle[files_list[5]]['[GEARS]'].pop('GEAR_' + str(i), None)
        window.Element('[GEARS]GEAR_' + str(i)).Update(value='')
        i += 1

    # update gear count
    window.Element('[GEARS]COUNT').Update(value=1)
    vehicle[files_list[5]]['[GEARS]']['COUNT'] = 1
    # update 1st gear ratio
    window.Element('[GEARS]GEAR_1').Update(value=0.67)
    vehicle[files_list[5]]['[GEARS]']['GEAR_1'] = 0.67
    # update final gear ratio
    window.Element('[GEARS]FINAL').Update(value=11.4)
    vehicle[files_list[5]]['[GEARS]']['FINAL'] = 11.4
    # update rpm limiter
    window.Element('[ENGINE_DATA]LIMITER').Update(value=rpm)
    vehicle[files_list[1]]['[ENGINE_DATA]']['LIMITER'] = rpm
    # update coast_ref rpm
    window.Element('[COAST_REF]RPM').Update(value=rpm + 500)
    vehicle[files_list[1]]['[COAST_REF]']['RPM'] = rpm + 500
    # create and reference new power.lut
    convertPowerFile(directory + ev_power_file_name)
    window.Element('[HEADER]POWER_CURVE').Update(value=ev_power_file_name)
    vehicle[files_list[1]]['[HEADER]']['POWER_CURVE'] = ev_power_file_name

    # ev torque file
    createTorqueLUTFile(rpm, torque, directory + ev_torque_file_name)
    # ev torque coast file
    createCoastLUTFile(rpm, directory + ev_coast_file_name)
    # ev gas file
    createDefaultEVFile(directory + ev_gas_file_name, 'Default Files/kers_gas.lut')
    # ev gear file
    createDefaultEVFile(directory + ev_gear_file_name, 'Default Files/kers_gear.lut')
    # ev slipratio file
    createDefaultEVFile(directory + ev_slipratio_file_name, 'Default Files/kers_slipratio.lut')
    # create ers file
    createDefaultEVFile(directory + ers_file, 'Default Files/ers.ini')
    # create ctrl_ers_0 file
    createDefaultEVFile(directory + ctrl_ers_file, 'Default Files/ctrl_ers_0.ini')


def createDefaultEVFile(file_directory, default_file):
    ev_file = open(file_directory, 'w')
    default_file_as_str = Path(default_file).read_text()
    ev_file.write(default_file_as_str)
    ev_file.close()


def convertPowerFile(directory):
    power_file = open(directory, 'w')
    i = 0
    while i < 2:
        power_file.write('0|0\n')
        i += 1
    power_file.close()


def createTorqueLUTFile(rpm, max_torque, directory):
    lut_file = open(directory, 'w')
    set_rpm = 0
    torque = max_torque
    while set_rpm < rpm + 300:
        if set_rpm < rpm * 0.45:
            pass
        elif torque < 100:
            torque *= 0.99
        elif set_rpm < rpm * 0.6:
            torque *= 0.95
        elif set_rpm < rpm * 0.8:
            torque *= 0.8
        elif set_rpm < rpm * 0.9:
            torque *= 0.7
        lut_file.write(str(set_rpm) + '|' + str(torque) + '\n')
        set_rpm += 500
    lut_file.close()


def createCoastLUTFile(rpm, directory):
    lut_file = open(directory, 'w')
    set_rpm = 0
    torque = 0
    while set_rpm <= rpm / 2:
        if set_rpm < 5500:
            torque = 20
        elif set_rpm < 6000:
            torque = 15
        elif set_rpm < 6500:
            torque = 11
        elif set_rpm < 7000:
            torque = 6
        else:
            torque = 3
        lut_file.write(str(set_rpm) + '|' + str(torque) + '\n')
        set_rpm += 500
    lut_file.close()


def writeValues(values, orig_path, new_path):
    for i in range(1, int(vehicle[orig_path + 'drivetrain.ini']['[GEARS]']['COUNT']) + 1):
        if values['[GEARS]GEAR_' + str(i)] != '' \
                and 'GEAR_' + str(i) not in vehicle[orig_path + 'drivetrain.ini']['[GEARS]']:
            vehicle[orig_path + 'drivetrain.ini']['[GEARS]']['GEAR_' + str(i)] = values['[GEARS]GEAR_' + str(i)]

    for file in vehicle:
        if new_path != '':  # save location was changed
            new_file_path = new_path + '/' + file.replace(orig_path, '')
            write = open(new_file_path, "w")
        lines = []
        for header in vehicle[file]:
            if header != "[HEADER]":
                lines.append("\n")
            lines.append(header + "\n")
            for key in vehicle[file][header]:
                if not ('GEAR_' in key and key[5] != 'R' and
                        int(key[5:]) > int(vehicle[orig_path + 'drivetrain.ini']['[GEARS]']['COUNT'])):
                    lines.append("{}={}\n".format(key, vehicle[file][header][key]))
        write.writelines(lines)


def updateLUTButtons(values):
    for value in values:
        if str(value).__contains__('LUT_') or str(value).__contains__('_CD') or str(value).__contains__('_CL'):
            if 'edit_' + value in window.AllKeysDict:
                if values[value] == '':
                    window.Element('edit_' + value).Update(disabled=True)
                else:
                    window.Element('edit_' + value).Update(disabled=False)


def lutCheck(event, directory, values):
    if event.__contains__('edit_LUT_') or event == 'edit_[HEADER]POWER_CURVE' \
            or event == 'edit_WEAR_CURVE' or event == 'edit_LUT' or event == 'edit_PERFORMANCE_CURVE':
        webbrowser.open(directory + values[event.replace('edit_', '')])


def updateLUTList():
    for file in files_list:
        if not file.__contains__('suspension') and not file.__contains__('brakes') \
                and not file.__contains__('drivetrain'):
            for header in vehicle[file]:
                for data in vehicle[file][header]:
                    if data.__contains__('LUT_') or data == 'WEAR_CURVE' or data == 'PERFORMANCE_CURVE' \
                            or data == 'LUT':
                        if data in window.AllKeysDict:
                            window.Element(data).Update(values=lut_list)
                    elif header + data == '[HEADER]POWER_CURVE':
                        if header + data in window.AllKeysDict:
                            window.Element(header + data).Update(values=lut_list)


def deleteTire(tire):
    front_tire = getHeader(tire, 'FRONT')
    rear_tire = getHeader(tire, 'REAR')
    vehicle[files_list[3]].pop(front_tire, None)
    vehicle[files_list[3]].pop(rear_tire, None)
    vehicle[files_list[3]].pop(front_tire.replace('[','['+'THERMAL_'), None)
    vehicle[files_list[3]].pop(rear_tire.replace('[','['+'THERMAL_'), None)
    tire_list.remove(tire)
    window.Element('tire_name').Update(values=tire_list, value=tire_list[0])
    window.Element('tire_location').Update(value='Front')
    window.Element('thermal_location').Update(value='Thermal_Front')
    if len(tire_list) < 2:
        window.Element('delete_tire').Update(disabled=True)
    updateTab(files_list[3], getHeader(tire_list[0], 'FRONT'))
    updateTab(files_list[3], getHeader(tire_list[0], 'THERMAL_FRONT'))


def addTire(directory, prev_lut, prev_thermal):
    new_tire = sg.popup_get_text(message='Name of new tire', title='NEW TIRE')

    if new_tire is not None and new_tire != '':
        front_lut = sg.popup_get_text(message='Name of front tire lut file', title='NEW TIRE')

        # key: WEAR_CURVE
        if front_lut is not None and front_lut != '':
            rear_lut = sg.popup_get_text(message='Name of rear tire lut file', title='NEW TIRE')
            front_thermal = sg.popup_get_text(message='Name of front thermal lut file', title='NEW TIRE')

            # key: PERFORMANCE_CURVE
            if front_thermal is not None and front_thermal != '':
                rear_thermal = sg.popup_get_text(message='Name of rear thermal lut file', title='NEW TIRE')

                # adds new tire to dict and updates window
                tire_list.append(new_tire)
                tires = tire_list[-1]
                addTireToDict(tires)
                window.Element('tire_name').Update(values=tire_list, value=tires)
                if len(tire_list) > 1:
                    window.Element('delete_tire').Update(disabled=False)

                # set front lut file in vehicle dict
                vehicle[files_list[3]][getHeader(new_tire, 'FRONT')]['WEAR_CURVE'] = front_lut + '.lut'
                # create front lut file in vehicle folder
                shutil.copy(directory + prev_lut, directory + front_lut + '.lut')
                # add to lut list and update window
                lut_list.append(front_lut + '.lut')

                # set front thermal lut file in vehicle dict
                vehicle[files_list[3]][getHeader(new_tire, 'THERMAL_FRONT')]['PERFORMANCE_CURVE'] \
                    = front_thermal + '.lut'
                # create front thermal file in vehicle folder
                shutil.copy(directory + prev_thermal, directory + front_thermal + '.lut')
                # add to lut list and update window
                lut_list.append(front_thermal + '.lut')

                # create front and rear lut file with same name
                if rear_lut is None or rear_lut == '':
                    # set value in vehicle dict first
                    vehicle[files_list[3]][getHeader(new_tire, 'REAR')]['WEAR_CURVE'] = front_lut + '.lut'
                # create front and rear lut with their different names
                elif rear_lut is not None and rear_lut != '':
                    vehicle[files_list[3]][getHeader(new_tire, 'REAR')]['WEAR_CURVE'] = rear_lut + '.lut'
                    shutil.copy(directory + prev_lut, directory + rear_lut + '.lut')
                    lut_list.append(rear_lut + '.lut')

                if rear_thermal is None or rear_thermal == '':
                    vehicle[files_list[3]][getHeader(new_tire, 'THERMAL_REAR')]['PERFORMANCE_CURVE'] \
                        = front_thermal + '.lut'
                elif rear_thermal is not None and rear_thermal != '':
                    vehicle[files_list[3]][getHeader(new_tire, 'THERMAL_REAR')]['PERFORMANCE_CURVE'] \
                        = rear_thermal + '.lut'
                    shutil.copy(directory + prev_thermal, directory + rear_thermal + '.lut')
                    lut_list.append(rear_thermal + '.lut')

                window.Element('WEAR_CURVE').Update(front_lut + '.lut')
                window.Element('PERFORMANCE_CURVE').Update(front_thermal + '.lut')
                updateLUTList()


def addTireToDict(tire_name):
    # get new header
    front_header = getNewTireHeader('FRONT')
    rear_header = getNewTireHeader('REAR')

    # create new dict in vehicle with key of new header
    # create headers for front, rear, and thermal front and rear

    # front
    vehicle[files_list[3]][front_header] = deepcopy(vehicle[files_list[3]][getHeader(tire_list[-2], 'FRONT')])
    vehicle[files_list[3]][front_header]['NAME'] = tire_name
    # rear
    vehicle[files_list[3]][rear_header] = deepcopy(vehicle[files_list[3]][getHeader(tire_list[-2], 'REAR')])
    vehicle[files_list[3]][rear_header]['NAME'] = tire_name
    # thermal_front
    vehicle[files_list[3]][getNewTireHeader('THERMAL_FRONT')] = deepcopy(vehicle[files_list[3]][
                                                                             getHeader(tire_list[-2], 'THERMAL_FRONT')])
    # thermal_rear
    vehicle[files_list[3]][getNewTireHeader('THERMAL_REAR')] = deepcopy(vehicle[files_list[3]][
                                                                            getHeader(tire_list[-2], 'THERMAL_REAR')])


def getNewTireHeader(key):
    count = 0
    prev_header = ''
    for header in vehicle[files_list[3]].keys():
        # get new front header
        if not key.__contains__('THERMAL'):
            if header.__contains__(key) and not header.__contains__('THERMAL'):
                count += 1
                prev_header = header
        else:
            if header.__contains__(key):
                count += 1
                prev_header = header

    # add count to header
    if prev_header[len(prev_header) - 2:len(prev_header) - 1].isnumeric():
        head_count = int(prev_header[len(prev_header) - 2:len(prev_header) - 1])
        return prev_header.replace(str(head_count), str(head_count + 1))
    else:  # set header count to 1 if header count was 0
        return prev_header[:int(len(prev_header)) - 1] + '_1]'


# gets header from given value
# returns first instance, front tire location for example
def getHeader(tires, location):
    for header in vehicle[files_list[3]].keys():
        if not header.__contains__('HEADER') and not header.__contains__('COMPOUND_DEFAULT'):
            if header.__contains__(location.upper()):
                if 'NAME' in vehicle[files_list[3]][header]:
                    if vehicle[files_list[3]][header]['NAME'] == tires:
                        return header
                elif location.upper().__contains__('THERMAL_'):
                    return header
    return  # should not end up here


# adds wing to wing list
# defaults values to the last wing in the wing list
def addWing(directory, prev_lift_lut, prev_height_lift, prev_drag_lut, prev_height_drag):
    lift_lut = sg.popup_get_text(message='Name of coefficient of lift lut file')
    height_lift = sg.popup_get_text(message='Name of height aero lift multiplier lut file or leave blank')
    drag_lut = sg.popup_get_text(message='Name of coefficient of drag lut file')
    height_drag = sg.popup_get_text(message='Name of height aero drag multiplier lut file or leave blank')

    valid_wing = False
    if lift_lut is not None and lift_lut != '' and drag_lut is not None and drag_lut != '':
        valid_wing = True
        wing_list.append('[WING_' + str(int(wing_list[-1][len(wing_list[-1]) - 2:len(wing_list[-1]) - 1]) + 1) + ']')
        vehicle[files_list[0]][wing_list[-1]] = deepcopy(vehicle[files_list[0]][wing_list[-2]])
        lift_lut = addLUTToStr(lift_lut)
        height_lift = addLUTToStr(height_lift)
        drag_lut = addLUTToStr(drag_lut)
        height_drag = addLUTToStr(height_drag)

    # set lut file in vehicle dict
    # create lut file in vehicle folder
    # add to lut list and update window
    if valid_wing:
        # lift_lut
        vehicle[files_list[0]][wing_list[-1]]['LUT_AOA_CL'] = lift_lut
        shutil.copy(directory + prev_lift_lut, directory + lift_lut)
        lut_list.append(lift_lut)
        # height_lift
        if height_lift is not None and height_lift != '':
            vehicle[files_list[0]][wing_list[-1]]['LUT_GH_CL'] = height_lift
            # not blank
            if prev_height_lift != '':
                shutil.copy(directory + prev_height_lift, directory + height_lift)
            else:
                open(directory + height_lift, 'a').close()
            lut_list.append(height_lift)
        # drag_lut
        vehicle[files_list[0]][wing_list[-1]]['LUT_AOA_CD'] = drag_lut
        shutil.copy(directory + prev_drag_lut, directory + drag_lut)
        lut_list.append(drag_lut)
        # height_drag
        if height_drag is not None and height_drag != '':
            vehicle[files_list[0]][wing_list[-1]]['LUT_GH_CD'] = height_drag
            # not blank
            if prev_height_drag != '':
                shutil.copy(directory + prev_height_drag, directory + height_drag)
            else:
                open(directory + height_drag, 'a').close()
            lut_list.append(height_drag)

        # update window
        window.Element('wing_name').Update(values=wing_list, value=wing_list[-1])
        if len(wing_list) > 1:
            window.Element('delete_wing').Update(disabled=False)
        window.Element('LUT_AOA_CL').Update(lift_lut)
        window.Element('LUT_GH_CL').Update(height_lift)
        window.Element('LUT_AOA_CD').Update(drag_lut)
        window.Element('LUT_GH_CD').Update(height_drag)
        updateLUTList()


# adds '.lut' to string if not already there
def addLUTToStr(string):
    if string is None or string == '':
        return string
    elif not string.__contains__('.lut'):
        string += '.lut'
    return string


def deleteWing(wing):
    vehicle[files_list[0]].pop(wing, None)
    wing_list.remove(wing)
    window.Element('wing_name').Update(values=wing_list, value=wing_list[0])
    window.Element('delete_wing').Update(disabled=True)


def addDynamicController(values):
    if len(dynamic_controller_list) < 1:
        dynamic_controller_list.append('[DYNAMIC_CONTROLLER_0]')
        window.Element('dynamic_controller').Update(values=dynamic_controller_list, value=dynamic_controller_list[-1])
        createBlankVals(files_list[0], dynamic_controller_list[-1], values)
        window.Element('delete_dynamic_controller').Update(disabled=False)
    else:
        dynamic_controller_list.append('[DYNAMIC_CONTROLLER_'
                                       + str(int(dynamic_controller_list[-1][len(dynamic_controller_list[-1])
                                                                             - 2:len(
            dynamic_controller_list[-1]) - 1]) + 1) + ']')
        window.Element('dynamic_controller').Update(values=dynamic_controller_list, value=dynamic_controller_list[-1])
        vehicle[files_list[0]][dynamic_controller_list[-1]] = deepcopy(
            vehicle[files_list[0]][dynamic_controller_list[-2]])


def deleteDynamicController(controller):
    vehicle[files_list[0]].pop(controller, None)
    dynamic_controller_list.remove(controller)
    if len(dynamic_controller_list) < 1:
        window.Element('dynamic_controller').Update(values=dynamic_controller_list, value='')
        window.Element('delete_dynamic_controller').Update(disabled=True)
    else:
        window.Element('dynamic_controller').Update(values=dynamic_controller_list, value=dynamic_controller_list[0])
        updateTab(files_list[0], dynamic_controller_list[0])


def createBlankVals(file, key, values):
    vehicle[file].setdefault(key, {})
    vehicle[file][key]['WING'] = values['WING']
    vehicle[file][key]['COMBINATOR'] = values['COMBINATOR']
    vehicle[file][key]['INPUT'] = values['INPUT']
    vehicle[file][key]['LUT'] = values['LUT']
    vehicle[file][key]['FILTER'] = values['FILTER']
    vehicle[file][key]['UP_LIMIT'] = values['UP_LIMIT']
    vehicle[file][key]['DOWN_LIMIT'] = values['DOWN_LIMIT']


def getFile(values):
    for file in files_list:
        if values['TABGROUP'] == 'ratios':
            return files_list[5]  # drivetrain file
        elif values['TABGROUP'] == 'car':
            return files_list[6]  # car file
        elif file.__contains__(values['TABGROUP']):
            return file


def updateWindow(file, header_list, values):
    for header in header_list:
        for data in vehicle[file][header]:
            if data in window.AllKeysDict and data in vehicle[file][header]:
                vehicle[file][header][data] = values[data]
                window.Element(data).Update(value=vehicle[file][header][data])
            else:
                if data == 'NAME' and file.__contains__('aero'):
                    vehicle[file][header][data] = values['WING_NAME']
                    window.Element('WING_NAME').Update(value=vehicle[file][header][data])
                elif data == 'TYPE' and file.__contains__('suspension'):
                    window.Element('SUSPENSION_TYPE').Update(value=vehicle[file][header][data])


# updates static GUI tabs - engine, ratios, drivetrain, car
def updateWindows(file, values):
    if values['[TURBO_0]LAG_DN'] != '' and '[TURBO_O]' not in vehicle[file].keys():
        # add new header to vehicle dictionary
        vehicle[file].setdefault('[TURBO_0]', {})
        for key in values.keys():
            if str(key).__contains__('[TURBO'):
                vehicle[file]['[TURBO_0]'].setdefault(key[9:], values[key])
            if str(key).__contains__('[FRONT]'):
                break

    for header in vehicle[file]:
        for data in vehicle[file][header]:
            if data in vehicle[file][header]:
                if data in window.AllKeysDict:
                    vehicle[file][header][data] = values[data]
                    window.Element(data).Update(value=vehicle[file][header][data])
                elif header + data in window.AllKeysDict:
                    vehicle[file][header][data] = values[header + data]
                    window.Element(header + data).Update(value=vehicle[file][header][data])


# updates drive type in drivetrain
def updateDriveType(file, drive_type, prev_type):
    vehicle[file]['[' + drive_type + ']'] = deepcopy(vehicle[file]['[' + prev_type + ']'])
    vehicle[file].pop('[' + prev_type + ']', None)


# updates dynamic GUI tabs - aero, tires, suspension
def updateTab(file, header):
    if header in vehicle[file]:
        for data in vehicle[file][header]:
            if data in window.AllKeysDict:
                window.Element(data).Update(value=vehicle[file][header][data])
            else:
                if data == 'NAME' and file.__contains__('aero'):
                    window.Element('WING_NAME').Update(value=vehicle[file][header][data])
                elif data == 'TYPE' and file.__contains__('suspension'):
                    window.Element('SUSPENSION_TYPE').Update(value=vehicle[file][header][data])


# updates ratios tab with correct amount of gears in the GUI
def updateRatios(values):
    if int(values['[GEARS]COUNT']) > 0:
        # reverse at the top
        window.Element('reverse_gear').Update(visible=True)

        # forward gears
        forward_gear_count = int(values['[GEARS]COUNT'])
        i = 1
        while i <= forward_gear_count:
            window.Element(str(i) + '_gear').Update(visible=True)
            i += 1
        # remove appropriate extra gears from GUI in case of downsize gears count
        if i < 11:
            while i < 11:
                window.Element(str(i) + '_gear').Update(visible=False)
                i += 1

        # final at the end
        window.Element('final_gear').Update(visible=True)


# can run through each ini file or call another method for each ini file
# key is str before the = and value is str after = in the ini file
# should have a list of all the ini files to automate selecting which file to look through
# pass in file and header
# currently: dict for every header for every list
def setValues(directory):
    files_list.extend([directory + 'aero.ini', directory + 'engine.ini', directory + 'suspensions.ini',
                       directory + 'tyres.ini', directory + 'brakes.ini', directory + 'drivetrain.ini',
                       directory + 'car.ini'])

    # loop:
    #   ini file -> header -> dict
    #
    #   for file in list:
    #       for header in file:
    #           dict
    for file in files_list:
        parser = Parser(file)
        vehicle.setdefault(file, parser.getData())
        for header in vehicle[file]:  # header: [GEARS]
            # AERO LIST SET UP
            if file.__contains__('aero'):
                updateWingLists(header)
            # TIRE LIST SET UP
            if file.__contains__('tyres'):
                updateTireLists(file, header)

            for data in vehicle[file][header]:  # data: COUNT
                if header + data in window.AllKeysDict or data in window.AllKeysDict:
                    # not aero, suspension, or tyres file
                    if file != files_list[0] and file != files_list[2] and file != files_list[3]:
                        window.Element(header + data).Update(value=vehicle[file][header][data])
                    else:
                        # use first wing for default aero file
                        if file == files_list[0] and header == '[WING_0]':
                            window.Element('WING_NAME').Update(value='BODY')
                            window.Element(data).Update(value=vehicle[file][header][data])
                        # use first dynamic controller for default aero file
                        elif file == files_list[0] and header == '[DYNAMIC_CONTROLLER_0]':
                            window.Element(data).Update(value=vehicle[file][header][data])
                        # use front tire and front thermal for tyre file
                        elif file == files_list[3]:
                            if header == '[FRONT]':
                                window.Element(data).Update(value=vehicle[file][header][data])
                            elif header == '[THERMAL_FRONT]':
                                window.Element(data).Update(value=vehicle[file][header][data])
                            else:
                                continue
                        # suspension file
                        elif file == files_list[2]:
                            if header != '[REAR]':
                                window.Element(data).Update(value=vehicle[file][header][data])
                        else:
                            continue
    setLUTList(directory)


def setPreviewImage(directory):
    # display preview image for current car else pull skin preview else pull badge
    image_directory = os.path.split(directory[:-1])[0] + '/'
    image_list = glob.glob(image_directory + '**/*preview*.*', recursive=True)
    if bool(image_list):
        if image_list[-1].split('.')[-1] == 'png':
            preview_directory = image_list[-1].replace('\\', '/')
            # print(preview_directory)
            window['preview_image'].update(preview_directory)
        elif image_list[0].split('.')[-1] == 'jpg':
            preview_directory = image_list[0].replace('\\', '/')
            preview_directory = Image.open(preview_directory)
            preview_directory.thumbnail((240, 120))
            bio = io.BytesIO()
            preview_directory.save(bio, format='PNG')
            window['preview_image'].update(data=bio.getvalue())
    else:
        image_list = glob.glob(image_directory + 'ui/badge.png')
        if bool(image_list):
            preview_directory = image_list[0].replace('\\', '/')
            window['preview_image'].update(preview_directory)
    window['preview_image'].update(visible=True)


def setLUTList(directory):
    for file in os.listdir(directory):
        # add new luts to lut list
        if file.__contains__('.lut') and file not in lut_list:
            lut_list.append(file)


def getName(header, index):
    i = 0
    for data in header.keys():
        if i == index:
            return header[data]
        i += 1
    return 'Name not found'


def updateWingLists(header):
    if header.__contains__('DYNAMIC_CONTROLLER'):
        dynamic_controller_list.append(header)
    elif not header.__contains__('HEADER'):
        wing_list.append(header)

    if not header.__contains__('HEADER'):
        window.Element('wing_name').Update(values=wing_list, value=wing_list[0])
        if len(dynamic_controller_list) > 1:
            window.Element('dynamic_controller').Update(values=dynamic_controller_list,
                                                        value=dynamic_controller_list[0])


def updateTireLists(file, header):
    if header.__contains__('FRONT') and not header.__contains__('THERMAL'):
        tire_list.append(vehicle[file][header]['NAME'])
        window.Element('tire_name').Update(values=tire_list, value=tire_list[0])
        window.Element('SHORT_NAME').Update(value=vehicle[file]['[FRONT]']['SHORT_NAME'])


if __name__ == '__main__':
    # Create the Window
    window = sg.Window('Assetto Corsa Vehicle Modifier', createWindowLayout(), size=(xSize, ySize),
                       resizable=True)

    # Run window event loop
    runLoop()

    # Close window at the end
    window.close()
