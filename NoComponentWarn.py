#Author-Thomas Axelsson
#Description-Warn when features are created outside components

# This file is part of NoComponentWarn, a Fusion 360 add-in that 
# warns when features are created outside components.
#
# Copyright (C) 2020  Thomas Axelsson
#
# NoComponentWarn is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NoComponentWarn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NoComponentWarn.  If not, see <https://www.gnu.org/licenses/>.

import adsk.core, adsk.fusion, adsk.cam, traceback

import ctypes
import os
import re
import sys

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

CREATION_COMMANDS_ = set([
    'SketchCreate',
    'PrimitiveBox',
    'PrimitiveCylinder',
    'PrimitiveSphere',
    'PrimitiveTorus',
    'PrimitiveCoil',
    'PrimitivePipe',
])

app_ = None
ui_ = None

error_catcher_ = thomasa88lib.error.ErrorCatcher(msgbox_in_debug=False)
events_manager_ = thomasa88lib.events.EventsManager(error_catcher_)
manifest_ = thomasa88lib.manifest.read()

disabled_for_documents_ = []
cmd_starting_handler_info_ = None

def command_handler(args):
    eventArgs = adsk.core.ApplicationCommandEventArgs.cast(args)
    
    #print("COMMAND", eventArgs.commandId, eventArgs.terminationReason, app_.activeEditObject.name, app_.activeEditObject.classType())

    # The quickest test first
    if app_.activeEditObject != app_.activeProduct.rootComponent:
        return

    # Checking disabled here. We would improve performance by checking in documentActivated, but
    # that event does not always fire (2020-08-02)
    # Bug: https://forums.autodesk.com/t5/fusion-360-api-and-scripts/api-bug-application-documentactivated-event-do-not-raise/m-p/9020750
    if app_.activeDocument in disabled_for_documents_:
        return

    if eventArgs.commandId not in CREATION_COMMANDS_:
        return

    # We must use "created" or "starting" to catch Box and the other solids.
    # If we execute our own command at that step, we abort the command the user
    # started. We could in theory re-execute that command, but we might lose
    # data(?). Going for a MessageBox instead.
    
    # Using a button combo with "Cancel", as that will map to Esc
    ret = thomasa88lib.win.msgbox.custom_msgbox('You are creating are creating a feature without any component.',
                                                f"No Component Warning (v {manifest_['version']})",
                                                (thomasa88lib.win.msgbox.MB_ICONWARNING |
                                                 thomasa88lib.win.msgbox.MB_CANCELTRYCONTINUE |
                                                 thomasa88lib.win.msgbox.MB_DEFBUTTON2),
                                                { thomasa88lib.win.msgbox.IDCANCEL: 'Cancel', # No localization
                                                  thomasa88lib.win.msgbox.IDTRYAGAIN: '&Continue',
                                                  thomasa88lib.win.msgbox.IDCONTINUE: "&Stop warning" })

    # Not checking for error. Just let user continue in that case.
    # Note the mapping of the labels in custom_msgbox()!
    if ret == thomasa88lib.win.msgbox.IDCANCEL:
        eventArgs.isCanceled = True
    elif ret == thomasa88lib.win.msgbox.IDCONTINUE:
        # Document.dataFile only works when the document is saved (then we can use "id")
        # Document.name always works but is the document name - include the vX version indicator.
        disabled_for_documents_.append(app_.activeDocument)

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
        
        if ui_.activeWorkspace.id == 'FusionSolidEnvironment':
            enable()

def stop(context):
    with error_catcher_:
        events_manager_.clean_up()
