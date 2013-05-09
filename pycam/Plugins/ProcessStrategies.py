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
import pycam.PathGenerators.PushCutter
import pycam.Toolpath.MotionGrid
from pycam.Toolpath.MotionGrid import START_X, START_Y, START_Z


_get_line_distance = lambda radius, overlap: 2 * radius * (1.0 - overlap)


class ProcessStrategySlicing(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamOverlap",
            "PathParamStepDown", "PathParamMaterialAllowance",
            "PathParamPattern"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"overlap": 0.1,
                "step_down": 1.0,
                "material_allowance": 0,
                "path_pattern": None,
        }
        self.core.register_parameter_set("process", "slicing",
                "Slice removal", self.run_process, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.unregister_parameter_set("process", "slicing")

    def run_process(self, process, tool_radius, (low, high)):
        line_distance = _get_line_distance(tool_radius,
                process["parameters"]["overlap"])
        path_generator = pycam.PathGenerators.PushCutter.PushCutter(waterlines=False)
        path_pattern = process["parameters"]["path_pattern"]
        path_get_func = self.core.get_parameter_sets(
                "path_pattern")[path_pattern["name"]]["func"]
        grid_func, kwargs = path_get_func(path_pattern)
        motion_grid = grid_func((low, high),
                process["parameters"]["step_down"],
                line_distance=line_distance, **kwargs)
        return path_generator, motion_grid


class ProcessStrategyContour(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "PathParamStepDown",
            "PathParamMaterialAllowance", "PathParamMillingStyle"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"step_down": 1.0,
                "material_allowance": 0,
                "overlap": 0.8,
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
        }
        self.core.register_parameter_set("process", "contour",
                "Waterline", self.run_process, parameters=parameters,
                weight=20)
        return True

    def teardown(self):
        self.core.unregister_parameter_set("process", "contour")

    def run_process(self, process, tool_radius, (low, high)):
        line_distance = _get_line_distance(tool_radius,
                process["parameters"]["overlap"])
        path_generator = pycam.PathGenerators.PushCutter.PushCutter(waterlines=True)
        # TODO: milling_style currently refers to the grid lines - not to the waterlines
        motion_grid = pycam.Toolpath.MotionGrid.get_fixed_grid(
                (low, high), process["parameters"]["step_down"],
                line_distance=line_distance,
                grid_direction=pycam.Toolpath.MotionGrid.GRID_DIRECTION_X, 
                milling_style=process["parameters"]["milling_style"])
        return path_generator, motion_grid


class ProcessStrategySurfacing(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamOverlap",
            "PathParamMaterialAllowance", "PathParamPattern"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"overlap": 0.6,
                "material_allowance": 0,
                "path_pattern": None,
        }
        self.core.register_parameter_set("process", "surfacing",
                "Surfacing", self.run_process, parameters=parameters,
                weight=50)
        return True

    def teardown(self):
        self.core.unregister_parameter_set("process", "surfacing")

    def run_process(self, process, tool_radius, (low, high)):
        line_distance = _get_line_distance(tool_radius,
                process["parameters"]["overlap"])
        path_generator = pycam.PathGenerators.DropCutter.DropCutter()
        path_pattern = process["parameters"]["path_pattern"]
        path_get_func = self.core.get_parameter_sets(
                "path_pattern")[path_pattern["name"]]["func"]
        grid_func, kwargs = path_get_func(path_pattern)
        motion_grid = grid_func((low, high), None,
                step_width=(tool_radius / 4.0),
                line_distance=line_distance, **kwargs)
        return path_generator, motion_grid


class ProcessStrategyEngraving(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamStepDown",
            "PathParamMillingStyle", "PathParamRadiusCompensation",
            "PathParamTraceModel", "PathParamPocketingType"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"step_down": 1.0,
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
                "radius_compensation": False,
                "trace_models": [],
                "pocketing_type": pycam.Toolpath.MotionGrid.POCKETING_TYPE_NONE,
        }
        self.core.register_parameter_set("process", "engraving",
                "Engraving", self.run_process, parameters=parameters,
                weight=80)
        return True

    def teardown(self):
        self.core.unregister_parameter_set("process", "engraving")

    def run_process(self, process, tool_radius, (low, high)):
        path_generator = pycam.PathGenerators.EngraveCutter.EngraveCutter()
        models = [m.model for m in process["parameters"]["trace_models"]]
        if not models:
            self.log.error("No trace models given: you need to assign a " + \
                    "2D model to the engraving process.")
            return None, None
        progress = self.core.get("progress")
        if process["parameters"]["radius_compensation"]:
            progress.update(text="Offsetting models")
            progress.set_multiple(len(models), "Model")
            compensated_models = []
            for index in range(len(models)):
                models[index] = models[index].get_offset_model(tool_radius,
                        callback=progress.update)
                progress.update_multiple()
            progress.finish()
        progress.update(text="Calculating moves")
        motion_grid = pycam.Toolpath.MotionGrid.get_lines_grid(models,
                (low, high), process["parameters"]["step_down"],
                line_distance=1.8*tool_radius,
                step_width=(tool_radius / 4.0),
                milling_style=process["parameters"]["milling_style"],
                pocketing_type=process["parameters"]["pocketing_type"],
                skip_first_layer=True, callback=progress.update)
        progress.finish()
        return path_generator, motion_grid

