# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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

from pycam.Toolpath import Bounds
import pycam.Cutters
import pycam.Utils.log
import ConfigParser
import StringIO
import os

log = pycam.Utils.log.get_logger()


class Settings(dict):

    GET_INDEX = 0
    SET_INDEX = 1
    VALUE_INDEX = 2

    def __getitem_orig(self, key):
        return super(Settings, self).__getitem__(key)

    def __setitem_orig(self, key, value):
        super(Settings, self).__setitem__(key, value)

    def add_item(self, key, get_func=None, set_func=None):
        self.__setitem_orig(key, [None, None, None])
        self.define_get_func(key, get_func)
        self.define_set_func(key, set_func)
        self.__getitem_orig(key)[self.VALUE_INDEX] = None

    def set(self, key, value):
        self.__setitem__(key,value)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def define_get_func(self, key, get_func=None):
        if not self.has_key(key):
            return
        if get_func is None:
            get_func = lambda: self.__getitem_orig(key)[self.VALUE_INDEX]
        self.__getitem_orig(key)[self.GET_INDEX] = get_func

    def define_set_func(self, key, set_func=None):
        if not self.has_key(key):
            return
        def default_set_func(value):
            self.__getitem_orig(key)[self.VALUE_INDEX] = value
        if set_func is None:
            set_func = default_set_func
        self.__getitem_orig(key)[self.SET_INDEX] = set_func

    def __getitem__(self, key):
        try:
            return self.__getitem_orig(key)[self.GET_INDEX]()
        except TypeError, err_msg:
            log.info("Failed to retrieve setting '%s': %s" % (key, err_msg))
            return None

    def __setitem__(self, key, value):
        if not self.has_key(key):
            self.add_item(key)
        self.__getitem_orig(key)[self.SET_INDEX](value)
        self.__getitem_orig(key)[self.VALUE_INDEX] = value

    def addmethod(self, name, method):
        """
        Add a class method
        """
        # Ensure that two methods with the same name can not be added
        if hasattr(self.__class__, name):
            raise AttributeError, \
                "Tried to add existing method '%s'" % name
        setattr(self.__class__, name, method)

    def delmethod(self, name):
        """
        Remove a class method
        """
        if not hasattr(self.__class__, name):
            raise AttributeError, \
                "Tried to delete non-existent method '%s'" % name
        delattr(self.__class__, name)


class ToolpathSettings(object):

    SECTIONS = {
        "Bounds": {
            "minx": float,
            "maxx": float,
            "miny": float,
            "maxy": float,
            "minz": float,
            "maxz": float,
        },
        "Tool": {
            "shape": str,
            "tool_radius": float,
            "torus_radius": float,
            "speed": float,
            "feedrate": float,
        },
        "Program": {
            "unit": str,
            "enable_ode": bool,
        },
        "Process": {
            "generator": str,
            "postprocessor": str,
            "path_direction": str,
            "material_allowance": float,
            "overlap_percent": int,
            "step_down": float,
            "engrave_offset": float,
            "milling_style": str,
            "pocketing_type": str,
        },
    }

    META_MARKER_START = "PYCAM_TOOLPATH_SETTINGS: START"
    META_MARKER_END = "PYCAM_TOOLPATH_SETTINGS: END"

    def __init__(self):
        self.program = {}
        self.bounds = {}
        self.tool_settings = {}
        self.process_settings = {}
        self.support_model = None

    def set_bounds(self, bounds):
        low, high = bounds.get_absolute_limits()
        self.bounds = {
                "minx": low[0],
                "maxx": high[0],
                "miny": low[1],
                "maxy": high[1],
                "minz": low[2],
                "maxz": high[2],
        }

    def get_bounds(self):
        low = (self.bounds["minx"], self.bounds["miny"], self.bounds["minz"])
        high = (self.bounds["maxx"], self.bounds["maxy"], self.bounds["maxz"])
        return Bounds(Bounds.TYPE_CUSTOM, low, high)

    def set_tool(self, index, shape, tool_radius, torus_radius=None, speed=0.0,
            feedrate=0.0):
        self.tool_settings = {"id": index,
                "shape": shape,
                "tool_radius": tool_radius,
                "torus_radius": torus_radius,
                "speed": speed,
                "feedrate": feedrate,
        }

    def get_tool(self):
        return pycam.Cutters.get_tool_from_settings(self.tool_settings)

    def get_tool_settings(self):
        return self.tool_settings

    def set_support_model(self, model):
        self.support_model = model

    def get_support_model(self):
        return self.support_model

    def set_calculation_backend(self, backend=None):
        self.program["enable_ode"] = (backend.upper() == "ODE")

    def get_calculation_backend(self):
        if self.program.has_key("enable_ode"):
            if self.program["enable_ode"]:
                return "ODE"
            else:
                return None
        else:
            return None

    def set_unit_size(self, unit_size):
        self.program["unit"] = unit_size

    def get_unit_size(self):
        if self.program.has_key("unit"):
            return self.program["unit"]
        else:
            return "mm"

    def set_process_settings(self, generator, postprocessor, path_direction,
            material_allowance=0.0, overlap_percent=0, step_down=1.0,
            engrave_offset=0.0, milling_style="ignore", pocketing_type="none"):
        # TODO: this hack should be somewhere else, I guess
        if generator in ("ContourFollow", "EngraveCutter"):
            material_allowance = 0.0
        self.process_settings = {
                "generator": generator,
                "postprocessor": postprocessor,
                "path_direction": path_direction,
                "material_allowance": material_allowance,
                "overlap_percent": overlap_percent,
                "step_down": step_down,
                "engrave_offset": engrave_offset,
                "milling_style": milling_style,
                "pocketing_type": pocketing_type,
        }

    def get_process_settings(self):
        return self.process_settings

    def parse(self, text):
        text_stream = StringIO.StringIO(text)
        config = ConfigParser.SafeConfigParser()
        config.readfp(text_stream)
        for config_dict, section in ((self.bounds, "Bounds"),
                (self.tool_settings, "Tool"),
                (self.process_settings, "Process")):
            for key, value_type in self.SECTIONS[section].items():
                value_raw = config.get(section, key, None)
                if value_raw is None:
                    continue
                elif value_type == bool:
                    value = value_raw.lower() in ("1", "true", "yes", "on")
                elif isinstance(value_type, basestring) \
                        and (value_type.startswith("list_of_")):
                    item_type = value_type[len("list_of_"):]
                    if item_type == "float":
                        item_type = float
                    else:
                        continue
                    try:
                        value = [item_type(one_val)
                                for one_val in value_raw.split(",")]
                    except ValueError:
                        log.warn("Settings: Ignored invalid setting due to " \
                                + "a failed list type parsing: " \
                                + "(%s -> %s): %s" % (section, key, value_raw))
                else:
                    try:
                        value = value_type(value_raw)
                    except ValueError:
                        log.warn("Settings: Ignored invalid setting " \
                                + "(%s -> %s): %s" % (section, key, value_raw))
                config_dict[key] = value

    def __str__(self):
        return self.get_string()

    def get_string(self):
        result = []
        for config_dict, section in ((self.bounds, "Bounds"),
                (self.tool_settings, "Tool"),
                (self.process_settings, "Process")):
            # skip empty sections
            if not config_dict:
                continue
            result.append("[%s]" % section)
            for key, value_type in self.SECTIONS[section].items():
                if config_dict.has_key(key):
                    value = config_dict[key]
                    if isinstance(value_type, basestring) \
                            and (value_type.startswith("list_of_")):
                        result.append("%s = %s" % (key,
                                ",".join([str(val) for val in value])))
                    elif type(value) == value_type:
                        result.append("%s = %s" % (key, value))
                # add one empty line after each section
            result.append("")
        return os.linesep.join(result)

