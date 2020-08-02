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

import os
import re
import sys

NAME = 'NoComponentWarn'

# Must import lib as unique name, to avoid collision with other versions
# loaded by other add-ins
from .thomasa88lib import events
from .thomasa88lib import manifest
from .thomasa88lib import error

# Force modules to be fresh during development
import importlib
importlib.reload(thomasa88lib.events)
importlib.reload(thomasa88lib.manifest)
importlib.reload(thomasa88lib.error)

COMPONENT_WARN_ID = 'thomasa88_componentWarn'

app_ = None
ui_ = None

error_catcher_ = thomasa88lib.error.ErrorCatcher(msgbox_in_debug=False)
events_manager_ = thomasa88lib.events.EventsManager(error_catcher_)
manifest_ = thomasa88lib.manifest.read()

warn_cmd_def_ = None
disabled_for_ = []

def command_terminated_handler(args):
    eventArgs = adsk.core.ApplicationCommandEventArgs.cast(args)
    
    #print("TERMINATED", eventArgs.commandId, eventArgs.terminationReason, app_.activeEditObject.classType())

    if eventArgs.commandId != 'SketchCreate':
        return
    
    # Checking here. We would improve performance by checking in documentActivated, but
    # that event does not always fire (2020-08-02)
    # Bug: https://forums.autodesk.com/t5/fusion-360-api-and-scripts/api-bug-application-documentactivated-event-do-not-raise/m-p/9020750
    if app_.activeDocument in disabled_for_:
        return

    # It does not matter if we catch the command in starting, creating or terminated;
    # Our "block" will always come later. We can do an inputBox() in starting to ask
    # early, but our action won't get through the event queue until after the sketch
    # is created, so there's no point.
    if eventArgs.commandId == 'SketchCreate' and app_.activeEditObject.parentComponent == app_.activeProduct.rootComponent:
        warn_cmd_def_.execute()

def warn_command_created_handler(args):
    eventArgs = adsk.core.CommandCreatedEventArgs.cast(args)

    # The nifty thing with cast is that code completion then knows the object type
    cmd = adsk.core.Command.cast(args.command)

    cmd.setDialogInitialSize(290, 130)
    cmd.setDialogMinimumSize(290, 130)

    events_manager_.add_handler(cmd.destroy,
                                adsk.core.CommandEventHandler,
                                warn_command_destroy_handler)
    
    events_manager_.add_handler(cmd.inputChanged,
                                adsk.core.InputChangedEventHandler,
                                warn_command_input_changed_handler)

    cmd.commandInputs.addTextBoxCommandInput('text1', 'This feature has no component.\nContinue?', '', 1, True)
    cmd.commandInputs.addBoolValueInput('disable', "Disable warning in this session", True, '', False)
    cmd.okButtonText = 'Continue (Enter)'
    cmd.cancelButtonText = 'Abort Feature (Esc)'

    # Don't spam the right click shortcut menu
    cmd.isRepeatable = False
    cmd.isExecutedWhenPreEmpted = False

def warn_command_input_changed_handler(args):
    eventArgs = adsk.core.InputChangedEventArgs.cast(args)
    if eventArgs.input.id == 'disable':
        global disabled_for_
        # Document.dataFile only works when the document is saved (then we can use "id")
        # Document.name always works but is the document name - include the vX version indicator.
        disabled_for_.append(app_.activeDocument)

def warn_command_destroy_handler(args):
    eventArgs = adsk.core.CommandEventArgs.cast(args)
    if eventArgs.terminationReason == adsk.core.CommandTerminationReason.CancelledTerminationReason:
        ui_.commandDefinitions.itemById('UndoCommand').execute()

def run(context):
    global app_
    global ui_
    global warn_cmd_def_
    with error_catcher_:
        app_ = adsk.core.Application.get()
        ui_ = app_.userInterface

        old_cmd_def = ui_.commandDefinitions.itemById(COMPONENT_WARN_ID)
        if old_cmd_def:
            old_cmd_def.deleteMe()

        warn_cmd_def_ = ui_.commandDefinitions.addButtonDefinition(COMPONENT_WARN_ID,
                                                                    f'No Component (v {manifest_["version"]})',
                                                                    '')

        events_manager_.add_handler(warn_cmd_def_.commandCreated,
                                    adsk.core.CommandCreatedEventHandler,
                                    warn_command_created_handler)

        events_manager_.add_handler(ui_.commandTerminated,
                                    adsk.core.ApplicationCommandEventHandler,
                                    command_terminated_handler)

def stop(context):
    with error_catcher_:
        events_manager_.clean_up()

        cmd_def = ui_.commandDefinitions.itemById(COMPONENT_WARN_ID)
        if cmd_def:
            cmd_def.deleteMe()
