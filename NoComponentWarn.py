#Author-Thomas Axelsson
#Description-Warn when features are created outside components

# This file is part of NoComponentWarn, a Fusion 360 add-in that 
# warns when features are created outside components.
#
# Copyright (c) 2020 Thomas Axelsson
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import adsk.core, adsk.fusion, adsk.cam, traceback

import ctypes
import os
import re
import sys
import time

NAME = 'NoComponentWarn'

# Must import lib as unique name, to avoid collision with other versions
# loaded by other add-ins
from .thomasa88lib import events
from .thomasa88lib import manifest
from .thomasa88lib import error
from .thomasa88lib.win import msgbox

# Force modules to be fresh during development
import importlib
importlib.reload(thomasa88lib.events)
importlib.reload(thomasa88lib.manifest)
importlib.reload(thomasa88lib.error)
importlib.reload(thomasa88lib.win.msgbox)

COMPONENT_WARN_ID = 'thomasa88_componentWarn'

# (command ID, is prefix)
CREATION_COMMANDS_ = [
    ('SketchCreate', False),
    ('Primitive', True),
    # 'WorkOffline' matches 'Work'-only prefix
    ('WorkPlane', True),
    ('WorkAxis', True),
    ('WorkPoint', True),
    ('Extrude', False),
    ('Revolve', False),
    ('Sweep', False),
    ('SolidLoft', False),
    ('FusionRibCommand', False),
    ('FusionWebCommand', False),
    ('EmbossCmd', False),
    ('FusionHoleCommand', False),
    ('FusionThreadCommand', False),
    ('PatternRectangular', False),
    ('PatternCircular', False),
    ('PatternOnPath', False),
    ('MirrorCommand', False),
    ('FusionSurfaceThickenCommand', False),
    ('SurfaceSculpt', False), # Boundary Fill
    ('SurfaceExtrude', False),
    ('SurfaceRevolve', False),
    ('SurfaceSweep', False),
    ('SurfaceLoft', False),
    ('FusionSurfacePatchCommand', False),
    ('FusionSurfaceRuledCommand', False),
    ('FusionSurfaceOffsetCommand', False),
]

app_ = None
ui_ = None

error_catcher_ = thomasa88lib.error.ErrorCatcher(msgbox_in_debug=False)
events_manager_ = thomasa88lib.events.EventsManager(error_catcher_)
manifest_ = thomasa88lib.manifest.read()

disabled_for_documents_ = []
cmd_starting_handler_info_ = None
# Hold-off timer. Sketch create button triggers 2 starting SketchCreate in a row.
last_continue_time_ = 0.0

def command_handler(args: adsk.core.ApplicationCommandEventArgs):
    global last_continue_time_
    
    #print("COMMAND", args.commandId, args.terminationReason, app_.activeEditObject.name, app_.activeEditObject.classType())
    #args.isCanceled = True

    # Checking disabled here. We would improve performance by checking in documentActivated, but
    # that event does not always fire (2020-08-02)
    # Bug: https://forums.autodesk.com/t5/fusion-360-api-and-scripts/api-bug-application-documentactivated-event-do-not-raise/m-p/9020750
    if app_.activeDocument in disabled_for_documents_:
        return
    
    if time.time() - last_continue_time_ < 3:
        # Sketch create button hold-off
        return

    for cmd, prefix in CREATION_COMMANDS_:
        if ((prefix and args.commandId.startswith(cmd)) or
            args.commandId == cmd):
            break
    else:
        return

    error_msg = None
    if app_.activeEditObject == app_.activeProduct.rootComponent:
        error_msg = 'You are creating a feature without any component.'
    else:
        for sel in ui_.activeSelections:
            if hasattr(sel, 'entity') and getattr(sel.entity, 'assemblyContext', None) is not None:
                if sel.entity.assemblyContext.component != app_.activeEditObject:
                    error_msg = 'You are creating a feature referencing another component.'
                    break

    if error_msg:
        # We must use "created" or "starting" to catch Box and the other solids.
        # Also, starting must be used for setting isCanceled.
        # If we execute our own command in starting or created, we abort the command the user
        # started. We could in theory re-execute that command, but we might lose
        # data(?). Going for a MessageBox together with isCanceled instead.
        
        # Using a button combo with "Cancel", as that will map to Esc
        ret = thomasa88lib.win.msgbox.custom_msgbox(error_msg,
                                                    f"No Component Warning (v {manifest_['version']})",
                                                    (thomasa88lib.win.msgbox.MB_ICONWARNING |
                                                    thomasa88lib.win.msgbox.MB_CANCELTRYCONTINUE |
                                                    thomasa88lib.win.msgbox.MB_DEFBUTTON2),
                                                    { thomasa88lib.win.msgbox.IDCANCEL: 'Cancel', # No localization
                                                    thomasa88lib.win.msgbox.IDTRYAGAIN: '&Continue',
                                                    thomasa88lib.win.msgbox.IDCONTINUE: "&Stop warning" })

        # Not checking for error return. Just let user continue in that case.
        # Note the mapping of the labels in custom_msgbox()!
        if ret == thomasa88lib.win.msgbox.IDCANCEL:
            # Cancel
            args.isCanceled = True
        elif ret == thomasa88lib.win.msgbox.IDCONTINUE:
            # Stop warning

            # Document.dataFile only works when the document is saved (then we can use "id")
            # Document.name always works but is the document name - include the vX version indicator.
            disabled_for_documents_.append(app_.activeDocument)
        else:
            # Continue
            last_continue_time_ = time.time()

def workspace_activated_handler(args: adsk.core.WorkspaceEventArgs):
    if args.workspace.id == 'FusionSolidEnvironment':
        enable()

def workspace_pre_deactivate_handler(args: adsk.core.WorkspaceEventArgs):
    disable()

def enable():
    global cmd_starting_handler_info_
    if not cmd_starting_handler_info_:
        cmd_starting_handler_info_ = events_manager_.add_handler(ui_.commandStarting,
                                                                 callback=command_handler)

def disable():
    global cmd_starting_handler_info_
    if cmd_starting_handler_info_:
        cmd_starting_handler_info_ = events_manager_.remove_handler(cmd_starting_handler_info_)

def run(context):
    global app_
    global ui_
    with error_catcher_:
        app_ = adsk.core.Application.get()
        ui_ = app_.userInterface
        
        events_manager_.add_handler(ui_.workspaceActivated,
                                    callback=workspace_activated_handler)
        
        events_manager_.add_handler(ui_.workspacePreDeactivate,
                                    callback=workspace_pre_deactivate_handler)
        
        if app_.isStartupComplete:
            # Cannot check the workspaces if Fusion is starting up.
            # Rely on the workspace event in that case.
            if ui_.activeWorkspace.id == 'FusionSolidEnvironment':
                enable()

def stop(context):
    with error_catcher_:
        events_manager_.clean_up()
