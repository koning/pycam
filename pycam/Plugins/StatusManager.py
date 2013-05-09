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

import pycam.Plugins
from pycam.Utils.locations import get_ui_file_location
from pycam.Utils.Persistence import Persistence, PersistenceException



class StatusManager(pycam.Plugins.PluginBase):
    """
    This class handles reading and writing all settings config files.

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
    CORE_METHODS = [
        'load_general_preferences',
        'save_general_preferences',
        'load_task_settings_file',
        'save_task_settings_file',
        ]
    PERSIST_GENERAL_PREFERENCES = \
        {'general' : [ "default_task_settings_file" ]}
    CONFIG_FILENAME_FILTER = (
        ("Config files", "*.conf"),
        )

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
            autoload_source = self.core.get_filechooserbutton(
                "Choose custom task settings file loading on startup",
                mode_load=True, type_filter=self.CONFIG_FILENAME_FILTER,
                parent=self.core.get("main_window"))
            autoload_box.add(autoload_source)
            autoload_source.show()
            def get_autoload_task_file(autoload_source=autoload_source):
                if autoload_enable.get_active():
                    # FIXME for some reason, get_filename doesn't work
                    # at the point the startup task file is loaded;
                    # however, it does start working later.  The
                    # initial set_filename works fine, so this hack
                    # gets the startup task file loaded even if it's
                    # ugly.
                    #
                    # return autoload_source.get_filename()
                    return autoload_source.get_filename() or \
                        dict(self.core)["default_task_settings_file"][2]
                else:
                    return None
            def set_autoload_task_file(filename):
                if filename:
                    autoload_enable.set_active(True)
                    autoload_box.show()
                    autoload_source.set_filename(filename)
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
            # FIXME This stuff REALLY needs to go into another
            # (Persistence?) class
            self.last_task_settings_file = None
            actiongroup = gtk.ActionGroup("task_settings")
            for objname, callback, accel_key, data in (
                ("LoadTaskSettings", self.load_task_settings_file, None, \
                     None),
                ("SaveTaskSettings", self.save_last_task_settings_file, None, \
                     None),
                ("SaveAsTaskSettings", self.save_task_settings_file, None, \
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
            
        self.persistence = Persistence()
        self.register_core_methods()
        return True


    def teardown(self):
        if self.gui:
            self.core.unregister_ui("preferences_general",
                                    "TaskSettingsDefaultFileBox")
            self.core.get("gtk-uimanager").remove_ui(self.ui_merge_menus)
        self.unregister_core_methods()

    def load_task_settings_file(self, widget=None, filename=None,
                                load_default=False, no_widget=False):
        """
        Load task settings from a file.  If filename is empty, bring
        up a chooser widget.

        load_default:  If set, load the default task settings file from
        general preferences (at startup).

        no_widget:  If set, never bring up a widget (for command line).
        """
        #FIXME much of this goes into Persistence
        if load_default:
            # Don't pop up a widget, just load the default file
            filename = self.core.get("default_task_settings_file")
        else:
            if not filename and not no_widget:
                # Pop up a widget
                filename = self.core.get_filename(
                    "Load task settings ...",
                    mode_load=True,
                    type_filter=self.CONFIG_FILENAME_FILTER)
                # Only update the last_task_settings attribute if the task
                # file was loaded interactively, i.e. ignore the initial
                # task file loading.
                if filename:
                    self.last_task_settings_file = filename
        if not filename:
            self.log.debug("No task settings filename specified; not loading")
            return
            
        # load task settings
        try:
            self.set_global_persist_data(
                'PERSIST_TASK_SETTINGS',
                self.persistence.load_data_file(filename))
            self.log.info("Task settings read from %s" % filename)
            self.core.add_to_recent_file_list(filename)
        except PersistenceException, e:
            self.log.error("Failed to load settings file %s:  %s" %
                           (filename, e.msg))
        #/FIXME

    def save_task_settings_file(self, widget=None, filename=None,
                                save_default=False, no_widget=False):
        """
        Save task settings to a file.  By default bring up a file
        chooser window; this can be used as a callback for the 'save
        task settings as...' menu item.  If the filename param is set,
        save to that file without opening a chooser window.

        save_default:  If set, load the 'default task settings file'
        from general preferences (used at startup).

        no_widget:  If set, never bring up a widget (for command line).
        """
        #FIXME much of this goes into Persistence
        if save_default:
            # Don't pop up a widget, just save the default file
            filename = self.core.get("default_task_settings_file")
        else:
            # get filename from dialog
            if not no_widget and (filename is None or not str(filename)):
                # open a file chooser dialog if no filename specified
                filename = self.core.get_filename(
                    "Save task settings ...", False,
                    self.CONFIG_FILENAME_FILTER, self.last_task_settings_file)
                # Only update the last_task_settings attribute if the task
                # file was loaded interactively, i.e. ignore the initial
                # task file loading.
                if filename:
                    self.last_task_settings_file = filename
        if not filename:
            self.log.debug("No task settings file specified; not saving")
            return

        # save task settings
        try:
            self.persistence.save_data_file(
                filename,
                self.get_global_persist_data('PERSIST_TASK_SETTINGS'))
            self.log.info("Task settings written to %s" % filename)
            self.core.add_to_recent_file_list(filename)
        except PersistenceException, e:
            self.log.error("Failed to save settings file %s:  %s" %
                           (filename, e.msg))
        #/FIXME

    def save_last_task_settings_file(self, widget=None, filename=None):
        """
        Save task settings to a file.  Present a file chooser window
        if the settings have never been loaded or saved from a chooser
        window before.  This is suitable behavior for the 'save task
        settings' menu item callback.
        """
        if filename is None:
            filename = self.last_task_settings_file
        self.save_task_settings_file(widget, filename)


    def get_global_persist_data(self, what):
        """
        Return a dict of merged plugin data suitable for storing.
        'what' should either be 'PERSIST_GENERAL_PREFERENCES' or
        'PERSIST_TASK_SETTINGS'.
        """
        result = {}
        for plugin in self.core.plugin_manager.get_plugins():
            if plugin.enabled:
                result = self._merge_state(result,
                                           plugin.get_persist_data(what))
        return result

    def set_global_persist_data(self, what, data):
        """
        Store a dict of merged plugin data back to modules.
        'what' should either be 'PERSIST_GENERAL_PREFERENCES' or
        'PERSIST_TASK_SETTINGS'.
        """
        for plugin in self.core.plugin_manager.get_plugins_sorted():
            if plugin.enabled:
                plugin.set_persist_data(what, data)


    def _merge_state(self, result, src):
        """ Recursive helper for get_global_persist_data """
        for key, value in src.items():
            if isinstance(value,dict):
                result[key] = self._merge_state(result.get(key,{}), src[key])
            else:
                result[key] = src[key]
        return result


    def load_general_preferences(self):
        """ load all settings that are available in the Preferences window from
        a file in the user's home directory """

        try:
            prefs = self.persistence.load_preferences_file()
        except PersistenceException, e:
            self.log.warn(e.message)
            return

        # save prefs to plugins
        self.set_global_persist_data('PERSIST_GENERAL_PREFERENCES', prefs)


    def save_general_preferences(self):
        """ save all settings that are available in the Preferences window to
        a file in the user's home directory """

        # get prefs from plugins
        prefs = self.get_global_persist_data('PERSIST_GENERAL_PREFERENCES')

        # write prefs to file
        try:
            self.persistence.save_preferences_file(prefs)
        except PersistenceException, e:
            # Problems saving the config may happen on occasion.  Log
            # as error and return.
            self.log.error(e.message)
            return

