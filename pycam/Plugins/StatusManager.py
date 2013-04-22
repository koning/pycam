# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

import yaml
# FIXME this needs to go into PluginBase class; see below
import gtk

import pycam.Utils.log
import pycam.Plugins
from pycam.Gui.Project import FILTER_CONFIG
from pycam.Utils.locations import get_ui_file_location

_log = pycam.Utils.log.get_logger()


class StatusManager(pycam.Plugins.PluginBase):
    """
    This class handles reading and writing task settings config files.

    Config files may be read under these conditions:
    - The '--config' switch is present on the command line
    - The 'default_task_settings_file' param is set in preferences.conf
    - The 'Load Task Settings...' file menu item is selected

    Config files are written when the 'Save Task Settings' or
    'Save Task Settings _as ...' file menu items are selected.
    """

    UI_FILE = "task_settings.ui"
    CATEGORIES = ["System"]
    GTKMENU_FILE = "task_settings_ui.xml"

    def setup(self):
        self._types = {}
        if self.gui:
            obj = self.gui.get_object('TaskSettingsDefaultFileBox')
            obj.unparent()
            self.core.register_ui("preferences_general", 
                                  "Task settings Default File",
                                  obj, 30)
            # autoload task settings file on startup
            autoload_enable = self.gui.get_object("AutoLoadTaskFile")
            autoload_box = self.gui.get_object("StartupTaskFileBox")
            autoload_source = self.gui.get_object("StartupTaskFile")
            # TODO: fix the extension filter
            #for one_filter in get_filters_from_list(FILTER_CONFIG):
            #    autoload_source.add_filter(one_filter)
            #    autoload_source.set_filter(one_filter)
            def get_autoload_task_file(autoload_source=autoload_source):
                if autoload_enable.get_active():
                    return autoload_source.get_filename()
                else:
                    return ""
            def set_autoload_task_file(filename):
                if filename:
                    autoload_enable.set_active(True)
                    autoload_box.show()
                    autoload_source.set_filename(filename)
                    _log.info("set_autoload_task_file:  set %s; read %s" %
                              (filename, autoload_source.get_filename()))
                else:
                    autoload_enable.set_active(False)
                    autoload_box.hide()
                    autoload_source.unselect_all()
            def autoload_enable_switched(widget, box):
                if not widget.get_active():
                    set_autoload_task_file(None)
                else:
                    autoload_box.show()
            autoload_enable.connect("toggled", autoload_enable_switched,
                    autoload_box)
            self.core.add_item("default_task_settings_file",
                    get_autoload_task_file, set_autoload_task_file)
            # Settings menu items
            # FIXME This stuff REALLY needs to go into the PluginBase class
            self.last_task_settings_file = None
            actiongroup = gtk.ActionGroup("task_settings")
            for objname, callback, accel_key, data in (
                ("LoadTaskSettings", self.load_task_settings_file, None, \
                     None),
                ("SaveTaskSettings", self.save_task_settings_file, None, \
                     None),
                ("SaveAsTaskSettings", self.save_as_task_settings_file, None, \
                     None),
                ):
                item = self.gui.get_object(objname)
                action = "activate"
                if data is None:
                    item.connect(action, callback)
                else:
                    item.connect(action, callback, data)
                actiongroup.add_action(item)
            uimanager = self.core.get("gtk-uimanager")
            uimanager.insert_action_group(actiongroup, pos=-1)
            gtkmenu_file = get_ui_file_location(self.GTKMENU_FILE)
            self.ui_merge_menus = uimanager.add_ui_from_file(gtkmenu_file)
            
        self.register_state_item(
            "gui-settings", "default_task_settings_file",
            self.core.getclosure("default_task_settings_file"),
            self.core.setclosure("default_task_settings_file"))
        return True

    def teardown(self):
        self.clear_state_items()
        if self.gui:
            self.core.unregister_ui("preferences_general",
                                    "TaskSettingsDefaultFileBox")
            self.core.get("gtk-uimanager").remove_ui(self.ui_merge_menus)

    def open_task_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_task_settings_file = filename
        self.load_task_settings_file(filename=filename)

    def load_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.core.get_filename_func(
                "Loading settings ...",
                mode_load=True,
                type_filter=FILTER_CONFIG)
            # Only update the last_task_settings attribute if the task
            # file was loaded interactively, i.e. ignore the initial
            # task file loading.
            if filename:
                self.last_task_settings_file = filename
        if filename:
            self.load_task_settings(filename)
            self.core.add_to_recent_file_list(filename)

    def save_as_task_settings_file(self, widget=None, filename=None,
                                   dialog_unless_filename=False):
        if callable(filename):
            filename = filename()
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)) \
                and not (filename and dialog_unless_filename):
            # we open a dialog
            filename = self.core.get_filename_func(
                "Save settings to ...",
                mode_load=False,
                type_filter=FILTER_CONFIG,
                filename_templates=[
                    pycam.Utils.URIHandler(self.last_task_settings_file)])
            if filename:
                self.last_task_settings_file = filename
        # no filename given -> exit
        if not filename:
            return
        try:
            out_file = open(filename, "w")
            out_file.write(self.dump_task_settings())
            out_file.close()
            _log.info("Task settings written to %s" % filename)
            self.core.add_to_recent_file_list(filename)
        except IOError:
            _log.error("Failed to save settings file")

    def save_task_settings_file(self, widget=None, filename=None):
        if filename is None:
            filename = self.last_task_settings_file
        self.save_as_task_settings_file(widget, filename, True)

    def load_task_settings(self, filename=None):
        settings = pycam.Gui.Settings.ProcessSettings()

        # if filename is None, then we're probably being called from
        # from the pycam executable, so look for a default file
        if filename is None:
            filename = self.core.get("default_task_settings_file")
            # Project.py defaults and preference file saves '' for None
            if filename == '':
                filename = None
            else:
                _log.info("filename: '%s'" % str(filename))
        if not filename is None:
            _log.info("Loading task settings file: %s" % str(filename))
            settings.load_file(filename)
        else:
            _log.debug("No task settings file defined; not loading")

        # flush all tables (without re-assigning new objects)
        for one_list_name in ("tool_settings", "process_settings", "bounds"):
            one_list = self.core.get(one_list_name)
            while one_list:
                one_list.pop()
        # TODO: load default tools/processes/bounds

    def save_task_settings(self, filename=None):
        settings = pycam.Gui.Settings.ProcessSettings()

        # FIXME:  not implemented
        _log.warning("Save task settings function not implemented")

    def gather_all_state(self):
        result = {"gui-settings" : {},
                  "task-settings" : {}}
        for plugin in self.core.plugin_manager.get_plugins():
            if plugin.enabled:
                plugin_state = plugin.dump_state()
                for section in plugin_state:
                    result[section].update(plugin.dump_state()[section])
        return result

    def dump_task_settings(self):
        state = self.gather_all_state()
        serialized_state = yaml.safe_dump(state["task-settings"],
                                          default_flow_style=False)
        return serialized_state
