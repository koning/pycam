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
import pycam.Gui.OpenGLTools
from pycam.Toolpath import MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID


class OpenGLViewToolpath(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow", "Toolpaths"]
    CATEGORIES = ["Toolpath", "Visualization", "OpenGL"]
    CORE_METHODS = ["draw_toolpath_moves_func"]

    def setup(self):
        import OpenGL.GL
        self._GL = OpenGL.GL
        self.core.register_event("visualize-items", self.draw_toolpaths)
        self.core.register_color("color_toolpath_cut", "Toolpath cut",
                60)
        self.core.register_color("color_toolpath_return",
                "Toolpath rapid", 70)
        self.core.register_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.register_display_item("show_toolpath", "Show Toolpath", 30),
        self.register_core_methods()
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_chain("get_draw_dimension",
                self.get_draw_dimension)
        self.core.unregister_event("visualize-items", self.draw_toolpaths)
        self.core.unregister_color("color_toolpath_cut")
        self.core.unregister_color("color_toolpath_return")
        self.core.unregister_display_item("show_toolpath")
        self.unregister_core_methods()
        self.core.emit_event("visual-item-updated")

    def get_draw_dimension(self, low, high):
        if self._is_visible():
            toolpaths = self.core.get("toolpaths").get_visible()
            for tp in toolpaths:
                mlow = tp.minx, tp.miny, tp.minz
                mhigh = tp.maxx, tp.maxy, tp.maxz
                if None in mlow or None in mhigh:
                    continue
                for index in range(3):
                    if (low[index] is None) or (mlow[index] < low[index]):
                        low[index] = mlow[index]
                    if (high[index] is None) or (mhigh[index] > high[index]):
                        high[index] = mhigh[index]

    def _is_visible(self):
        return self.core.get("show_toolpath") \
                and not self.core.get("toolpath_in_progress") \
                and not self.core.get("show_simulation")

    def draw_toolpaths(self):
        if self._is_visible():
            # TODO: this is ugly copy'n'paste from pycam.Plugins.ToolpathExport (_export_toolpaths)
            # KEEP IN SYNC
            processor = self.core.get("toolpath_processors").get_selected()
            if not processor:
                self.log.warn("No toolpath processor selected")
                return
            filter_func = processor["func"]
            filter_params = self.core.get_parameter_values(
                    "toolpath_processor")
            settings_filters = filter_func(filter_params)
            for toolpath in self.core.get("toolpaths").get_visible():
                # TODO: enable the VBO code for speedup!
                #moves = toolpath.get_moves_for_opengl(self.core.get("gcode_safety_height"))
                #self._draw_toolpath_moves2(moves)
                moves = toolpath.get_basic_moves(filters=settings_filters)
                self.draw_toolpath_moves_func(moves)
            
    def _draw_toolpath_moves2(self, paths):
        GL = self._GL
        GL.glDisable(GL.GL_LIGHTING)
        color_rapid = self.core.get("color_toolpath_return")
        color_cut = self.core.get("color_toolpath_cut")
        show_directions = self.core.get("show_directions")
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        coords = paths[0]
        try:
            coords.bind()
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glVertexPointerf(coords)
            for path in paths[1]:
                if path[2]:
                    GL.glColor4f(color_rapid["red"], color_rapid["green"], color_rapid["blue"], color_rapid["alpha"])
                else:
                    GL.glColor4f(color_cut["red"], color_cut["green"], color_cut["blue"], color_cut["alpha"])
                if show_directions:
                    GL.glDisable(GL.GL_CULL_FACE)
                    GL.glDrawElements(GL.GL_TRIANGLES, len(path[1]), GL.GL_UNSIGNED_INT, path[1])
                    GL.glEnable(GL.GL_CULL_FACE)
                GL.glDrawElements(GL.GL_LINE_STRIP, len(path[0]), GL.GL_UNSIGNED_INT, path[0])
        finally:
            coords.unbind()

    ## Simulate still depends on this pathway
    def draw_toolpath_moves_func(self, moves):
        GL = self._GL
        GL.glDisable(GL.GL_LIGHTING)
        show_directions = self.core.get("show_directions")
        color_rapid = self.core.get("color_toolpath_return")
        color_cut = self.core.get("color_toolpath_cut")
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        last_position = None
        last_rapid = None
        GL.glBegin(GL.GL_LINE_STRIP)
        for move_type, position in moves:
            if not move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                continue
            rapid = move_type == MOVE_STRAIGHT_RAPID
            if last_rapid != rapid:
                GL.glEnd()
                if rapid:
                    GL.glColor4f(color_rapid["red"], color_rapid["green"],
                            color_rapid["blue"], color_rapid["alpha"])
                else:
                    GL.glColor4f(color_cut["red"], color_cut["green"],
                            color_cut["blue"], color_cut["alpha"])
                # we need to wait until the color change is active
                GL.glFinish()
                GL.glBegin(GL.GL_LINE_STRIP)
                if not last_position is None:
                    GL.glVertex3f(*last_position)
                last_rapid = rapid
            GL.glVertex3f(*position)
            last_position = position
        GL.glEnd()
        if show_directions:
            for index in range(len(moves) - 1):
                p1 = moves[index][0]
                p2 = moves[index + 1][0]
                pycam.Gui.OpenGLTools.draw_direction_cone(p1, p2)

