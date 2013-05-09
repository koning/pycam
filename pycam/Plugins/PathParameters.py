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


import pycam.Plugins
import pycam.Gui.ControlsGTK
import pycam.Toolpath.MotionGrid


class PathParamOverlap(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        # configure the input/output converter
        self.control = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=99,
                digits=0, increment=10, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.control.set_conversion(
                set_conv=lambda float_value: int(float_value * 100.0),
                get_conv=lambda percent: percent / 100.0)
        self.core.register_parameter("process", "overlap",
                self.control)
        self.core.register_ui("process_path_parameters", "Overlap [%]",
                self.control.get_widget(), weight=10)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("process", "overlap")


class PathParamStepDown(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(lower=0.01,
                upper=1000, digits=2, start=1,
                change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.core.register_parameter("process", "step_down",
                self.control)
        self.core.register_ui("process_path_parameters", "Step down",
                self.control.get_widget(), weight=20)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("process", "step_down")


class PathParamMaterialAllowance(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(start=0, lower=0,
                upper=100, digits=2, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.core.register_parameter("process", "material_allowance",
                self.control)
        self.core.register_ui("process_path_parameters", "Material allowance",
                self.control.get_widget(), weight=30)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("process", "material_allowance")


class PathParamMillingStyle(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "PathParamPattern"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                    (("ignore", pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE),
                    ("climb / down", pycam.Toolpath.MotionGrid.MILLING_STYLE_CLIMB),
                    ("conventional / up", pycam.Toolpath.MotionGrid.MILLING_STYLE_CONVENTIONAL)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.register_parameter("path_pattern", "milling_style",
                self.control)
        self.core.register_parameter("process", "milling_style",
                self.control)
        self.core.register_ui("process_path_parameters", "Milling style",
                self.control.get_widget(), weight=50)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("path_pattern", "milling_style")
        self.core.unregister_parameter("process", "milling_style")


class PathParamGridDirection(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "PathParamPattern"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                    (("x", pycam.Toolpath.MotionGrid.GRID_DIRECTION_X),
                    ("y", pycam.Toolpath.MotionGrid.GRID_DIRECTION_Y),
                    ("xy", pycam.Toolpath.MotionGrid.GRID_DIRECTION_XY)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.register_parameter("path_pattern", "grid_direction",
                self.control)
        self.core.register_parameter("process", "grid_direction",
                self.control)
        self.core.register_ui("process_path_parameters", "Direction",
                self.control.get_widget(), weight=40)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("path_pattern", "grid_direction")
        self.core.unregister_parameter("process", "grid_direction")


class PathParamSpiralDirection(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "PathParamPattern"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                    (("outside -> center", pycam.Toolpath.MotionGrid.SPIRAL_DIRECTION_IN),
                    ("center -> outside", pycam.Toolpath.MotionGrid.SPIRAL_DIRECTION_OUT)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.register_parameter("path_pattern", "spiral_direction",
                self.control)
        self.core.register_ui("process_path_parameters", "Direction",
                self.control.get_widget(), weight=40)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("path_pattern", "spiral_direction")


class PathParamPattern(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "ParameterGroupManager"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.choices = []
        self.control = pycam.Gui.ControlsGTK.InputChoice([],
                change_handler=lambda widget=None: self.core.emit_event(
                    "process-changed"))
        self.control.set_conversion(set_conv=self._set_value_converter,
                get_conv=self._get_value_converter)
        self.core.register_parameter("process", "path_pattern",
                self.control)
        self.core.register_parameter_group("path_pattern",
                changed_set_event="process-path-pattern-changed",
                changed_set_list_event="process-path-pattern-list-changed",
                get_current_set_func=self._get_pattern)
        self.core.register_ui("process_path_parameters", "Pattern",
                self.control.get_widget(), weight=5)
        self.control.get_widget().connect("changed", lambda widget: \
                self.core.emit_event("process-path-pattern-changed"))
        self.core.register_event("process-path-pattern-list-changed",
                self._update_selector)
        return True

    def _get_value_converter(self, value):
        if value:
            pattern_sets = self.core.get_parameter_sets("path_pattern")
            try:
                current_pattern_set = pattern_sets[value]
            except KeyError:
                return None
            parameter_keys = current_pattern_set["parameters"].keys()
            all_parameters = self.core.get_parameter_values("path_pattern")
            result = {"name": value, "parameters": {}}
            for parameter_key in parameter_keys:
                result["parameters"][parameter_key] = all_parameters[parameter_key]
            return result
        else:
            return None

    def _set_value_converter(self, value):
        if value:
            self.core.set_parameter_values("path_pattern", value["parameters"])
            return value["name"]
        elif self.choices:
            # use the first entry as the default value
            return self.choices[0][1]
        else:
            return None

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_event("process-path-pattern-list-changed",
                self._update_selector)
        self.core.unregister_parameter("process", "path_pattern")
        self.core.unregister_parameter_group("path_pattern")


    def _update_selector(self):
        patterns = list(self.core.get_parameter_sets("path_pattern").values())
        patterns.sort(key=lambda item: item["weight"])
        self.choices = []
        for pattern in patterns:
            self.choices.append((pattern["label"], pattern["name"]))
        self.control.update_choices(self.choices)
        if not self.control.get_value() and self.choices:
            self.control.set_value({"name": self.choices[0][1], "parameters": {}})

    def _get_pattern(self):
        pattern_set = self.control.get_value()
        if pattern_set:
            return self.core.get_parameter_sets("path_pattern")[
                pattern_set["name"]]
        else:
            return None


class PathParamRoundedSpiralCorners(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputCheckBox(
                change_handler=lambda widget=None: self.core.emit_event(
                    "process-changed"))
        self.core.register_parameter("path_pattern", "rounded_corners",
                self.control)
        self.core.register_ui("process_path_parameters", "Rounded corners",
                self.control.get_widget(), weight=80)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters",
                self.control.get_widget())
        self.core.unregister_parameter("path_pattern", "rounded_corners")


class PathParamRadiusCompensation(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputCheckBox(
                change_handler=lambda widget=None: self.core.emit_event(
                    "process-changed"))
        self.core.register_parameter("process", "radius_compensation",
                self.control)
        self.core.register_ui("process_path_parameters", "Radius compensation",
                self.control.get_widget(), weight=80)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("process", "radius_compensation")


class PathParamTraceModel(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "Models"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputTable([],
                change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        # configure the input/output converter
        def get_converter(model_refs):
            models_dict = {}
            for model in self.core.get("models"):
                models_dict[id(model)] = model
            models = []
            for model_ref in model_refs:
                if model_ref in models_dict:
                    models.append(models_dict[model_ref])
            return models
        def set_converter(models):
            return [id(model) for model in models]
        self.control.set_conversion(set_conv=set_converter,
                get_conv=get_converter)
        self.core.register_parameter("process", "trace_models",
                self.control)
        self.core.register_ui("process_path_parameters", "Trace models (2D)",
                self.control.get_widget(), weight=5)
        self.core.register_event("model-list-changed", self._update_models)
        return True

    def teardown(self):
        self.core.unregister_parameter("process", "trace_models")
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_event("model-list-changed", self._update_models)

    def _update_models(self):
        choices = []
        models = self.core.get("models")
        for model in models:
            if hasattr(model.model, "get_polygons"):
                choices.append((model["name"], model))
        self.control.update_choices(choices)


class PathParamPocketingType(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                    (("none", pycam.Toolpath.MotionGrid.POCKETING_TYPE_NONE),
                    ("holes", pycam.Toolpath.MotionGrid.POCKETING_TYPE_HOLES),
                    ("material", pycam.Toolpath.MotionGrid.POCKETING_TYPE_MATERIAL)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.register_parameter("process", "pocketing_type",
                self.control)
        self.core.register_ui("process_path_parameters", "Pocketing",
                self.control.get_widget(), weight=60)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_parameter("path_pattern", "pocketing_type")

