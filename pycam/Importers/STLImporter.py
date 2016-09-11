# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008-2010 Lode Leroy
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

from pycam.Geometry.PointUtils import *
from pycam.Geometry.Triangle import Triangle
from pycam.Geometry.PointKdtree import PointKdtree
from pycam.Geometry.utils import epsilon
from pycam.Geometry.Model import Model
import pycam.Utils.log
import pycam.Utils

from struct import unpack 
import StringIO
import re

import time
from stl import mesh

log = pycam.Utils.log.get_logger()


vertices = 0
edges = 0
kdtree = None

lastUniqueVertex = (None,None,None)
def UniqueVertex(x, y, z):
    global vertices,lastUniqueVertex
    if kdtree:
        p = kdtree.Point(x, y, z)
        if p == lastUniqueVertex:
            vertices += 1
        return p
    else:
        vertices += 1
        return (x, y, z)

def ImportModel(filename, use_kdtree=True, callback=None, **kwargs):
    global vertices, edges, kdtree
    vertices = 0
    edges = 0
    kdtree = None

    normal_conflict_warning_seen = False
    
    sTime = time.time()
    
    # Package numpy-stl (https://github.com/WoLpH/numpy-stl) handles all loading of
    #  the STL files. PyCam will only do a cursory post-processing, notably around
    #  validating the Normals and the actual Triangles in the STL
    loaded_mesh = mesh.Mesh.from_file(filename, calculate_normals=False)

    if use_kdtree:
        kdtree = PointKdtree([], 3, 1, epsilon)
    model = Model(use_kdtree)

    t = None
    p1 = None
    p2 = None
    p3 = None
    
    current_facet = 0
    
    for FACET in loaded_mesh.data:
        current_facet += 1
        if callback and callback():
            log.warn("STLImporter: load model operation cancelled")
            return None
                
        n = (FACET[0][0], FACET[0][1], FACET[0][2], 'v')
        p1 = (FACET[1][0][0], FACET[1][0][1], FACET[1][0][2])
        p2 = (FACET[1][1][0], FACET[1][1][1], FACET[1][1][2])
        p3 = (FACET[1][2][0], FACET[1][2][1], FACET[1][2][2])
        
        
        # validate the normal
        # The three vertices of a triangle in an STL file are supposed
        # to be in counter-clockwise order. This should match the
        # direction of the normal.
        if n is None:
            # invalid triangle (zero-length vector)
            dotcross = 0
        else:
            # make sure the points are in ClockWise order
            dotcross = pdot(n, pcross(psub(p2,p1), psub(p3, p1)))
        if dotcross > 0:
            # Triangle expects the vertices in clockwise order
            t = Triangle(p1, p3, p2, n)
        elif dotcross < 0:
            if not normal_conflict_warning_seen:
                log.warn(("Inconsistent normal/vertices found in " + \
                        "facet %d of '%s'. Please validate the STL " + \
                        "file!") % (current_facet, filename))
                normal_conflict_warning_seen = True
            t = Triangle(p1, p2, p3, n)
        else:
            # The three points are in a line - or two points are
            # identical. Usually this is caused by points, that are too
            # close together. Check the tolerance value in
            # pycam/Geometry/PointKdtree.py.
            log.warn("Skipping invalid triangle: %s / %s / %s " \
                    % (p1, p2, p3) + "(maybe the resolution of the " \
                    + "model is too high?)")
            n, p1, p2, p3 = (None, None, None, None)
            
        n, p1, p2, p3 = (None, None, None, None)
        model.append(t)
        
    log.info("Imported STL model: %d triangles in %.4f seconds." \
            % (len(model.triangles()), time.time() - sTime))
    vertices = 0
    edges = 0
    kdtree = None

    if not model:
        # no valid items added to the model
        return None
    else:
        return model
    
