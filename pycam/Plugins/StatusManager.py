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

# FIXME:  these belong in a persistence module; see below
#import os
import xml.etree.ElementTree as ET

import pycam.Utils.log
import pycam.Plugins
from pycam.Gui.Project import FILTER_CONFIG

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

    def open_task_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
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
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        if filename:
            self.load_task_settings(filename)
            self.core.add_to_recent_file_list(filename)

    def save_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)):
            # we open a dialog
            filename = self.core.get_filename_func(
                "Save settings to ...",
                mode_load=False,
                type_filter=FILTER_CONFIG,
                filename_templates=(self.last_task_settings_uri,
                                    self.last_model_uri))
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        # no filename given -> exit
        if not filename:
            return
        settings = self.core.dump_state()
        try:
            out_file = open(filename, "w")
            out_file.write(settings)
            out_file.close()
            _log.info("Task settings written to %s" % filename)
            self.core.add_to_recent_file_list(filename)
        except IOError:
            log.error("Failed to save settings file")

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

    def dump_all_state(self):
        result = {"gui-settings" : {},
                  "task-settings" : {}}
        for plugin in self.core.plugin_manager.get_plugins():
            if plugin.enabled:
                plugin_state = plugin.dump_state()
                for section in plugin_state:
                    result[section].update(plugin.dump_state()[section])
        return result
        # FIXME:  these belong in a persistence module
        # root = ET.Element("pycam")
        # for match, element in result:
        #     chain = match.split("/")
        #     if not hasattr(element, "findtext"):
        #         # not an instance of ET.Element
        #         element = _get_xml(element, chain[-1])
        #     parent = root
        #     if match:
        #         for component in chain[:-1]:
        #             next_item = parent.find(component)
        #             if not next_item is None:
        #                 parent = next_item
        #             else:
        #                 item = ET.SubElement(parent, component)
        #                 parent = item
        #     parent.append(element)
        # return os.linesep.join(_get_xml_lines(root))


def _get_xml(item, name=None):
    if name is None:
        if hasattr(item, "node_key"):
            name = item.node_key
        else:
            name = "value"
    if isinstance(item, (list, tuple, set)):
        leaf = ET.Element(name)
        leaf.attrib["type"] = str(type(item))
        for single in item:
            leaf.append(_get_xml(single))
        return leaf
    elif isinstance(item, dict):
        leaf = ET.Element(name)
        leaf.attrib["type"] = "dict"
        for key, value in item.iteritems():
            leaf.append(_get_xml(value, name=key))
        return leaf
    else:
        leaf = ET.Element(name)
        leaf.text = str(item)
        leaf.attrib["type"] = str(type(item))
        return leaf


def _get_xml_lines(item):
    lines = []
    content = ET.tostring(item)
    content = content.replace("><", ">\n<")
    indent = 0
    for line in content.split("\n"):
        indented = False
        if line.startswith("</"):
            indent -= 2
            indented = True
        lines.append(" " * indent + line)
        if indented:
            pass
        elif line.endswith("/>"):
            pass
        elif line.startswith("</"):
            indent -= 2
        elif "</" in line:
            pass
        else:
            indent += 2
    return lines

