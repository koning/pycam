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
    
    loaded_mesh = mesh.Mesh.from_file(filename)

    if hasattr(filename, "read"):
        # make sure that the input stream can seek and has ".len"
        f = StringIO.StringIO(filename.read())
        # useful for later error messages
        filename = "input stream"
    else:
        try:
            url_file = pycam.Utils.URIHandler(filename).open()
            # urllib.urlopen objects do not support "seek" - so we need to read
            # the whole file at once. This is ugly - anyone with a better idea?
            f = StringIO.StringIO(url_file.read())
            # TODO: the above ".read" may be incomplete - this is ugly
            # see http://patrakov.blogspot.com/2011/03/case-of-non-raised-exception.html
            # and http://stackoverflow.com/questions/1824069/urllib2-not-retrieving-entire-http-response
            url_file.close()
        except IOError, err_msg:
            log.error("STLImporter: Failed to read file (%s): %s" \
                    % (filename, err_msg))
            return None
    # Read the first two lines of (potentially non-binary) input - they should
    # contain "solid" and "facet".
    header_lines = []
    while len(header_lines) < 2:
        line = f.readline(200)
        if len(line) == 0:
            # empty line (not even a line-feed) -> EOF
            log.error("STLImporter: No valid lines found in '%s'" % filename)
            return None
        # ignore comment lines
        # note: partial comments (starting within a line) are not handled
        if not line.startswith(";"):
            header_lines.append(line)
    header = "".join(header_lines)
    # read byte 80 to 83 - they contain the "numfacets" value in binary format
    f.seek(80)
    numfacets = unpack("<I", f.read(4))[0]
    binary = False
    log.debug("STL import info: %s / %s / %s / %s" % \
            (f.len, numfacets, header.find("solid"), header.find("facet")))

    if f.len == (84 + 50*numfacets):
        binary = True
    elif header.find("solid") >= 0 and header.find("facet") >= 0:
        binary = False
        f.seek(0)
    else:
        log.error("STLImporter: STL binary/ascii detection failed")
        return None

    if use_kdtree:
        kdtree = PointKdtree([], 3, 1, epsilon)
    model = Model(use_kdtree)

    t = None
    p1 = None
    p2 = None
    p3 = None

    if binary:
        for i in range(1, numfacets + 1): 
            if callback and callback():
                log.warn("STLImporter: load model operation cancelled")
                return None
            a1 = unpack("<f", f.read(4))[0] 
            a2 = unpack("<f", f.read(4))[0] 
            a3 = unpack("<f", f.read(4))[0] 

            n = (float(a1), float(a2), float(a3), 'v')
            
            v11 = unpack("<f", f.read(4))[0] 
            v12 = unpack("<f", f.read(4))[0] 
            v13 = unpack("<f", f.read(4))[0] 

            p1 = UniqueVertex(float(v11), float(v12), float(v13))
            
            v21 = unpack("<f", f.read(4))[0] 
            v22 = unpack("<f", f.read(4))[0] 
            v23 = unpack("<f", f.read(4))[0] 

            p2 = UniqueVertex(float(v21), float(v22), float(v23))
            
            v31 = unpack("<f", f.read(4))[0] 
            v32 = unpack("<f", f.read(4))[0] 
            v33 = unpack("<f", f.read(4))[0] 
            
            p3 = UniqueVertex(float(v31), float(v32), float(v33))

            # not used
            attribs = unpack("<H", f.read(2)) 
            
            dotcross = pdot(n, pcross(psub(p2, p1), psub(p3, p1)))
            if a1 == a2 == a3 == 0:
                dotcross = pcross(psub(p2, p1), psub(p3,p1))[2]
                n = None

            if dotcross > 0:
                # Triangle expects the vertices in clockwise order
                t = Triangle(p1, p3, p2)
            elif dotcross < 0:
                if not normal_conflict_warning_seen:
                    log.warn(("Inconsistent normal/vertices found in facet " + \
                            "definition %d of '%s'. Please validate the " + \
                            "STL file!") % (i, filename))
                    normal_conflict_warning_seen = True
                t = Triangle(p1, p2, p3)
            else:
                # the three points are in a line - or two points are identical
                # usually this is caused by points, that are too close together
                # check the tolerance value in pycam/Geometry/PointKdtree.py
                log.warn("Skipping invalid triangle: %s / %s / %s " \
                        % (p1, p2, p3) + "(maybe the resolution of the model " \
                        + "is too high?)")
                continue
            if n:
                t.normal = n

            model.append(t)
    else:
        solid = re.compile(r"\s*solid\s+(\w+)\s+.*")
        endsolid = re.compile(r"\s*endsolid\s*")
        facet = re.compile(r"\s*facet\s*")
        normal = re.compile(r"\s*facet\s+normal" \
                + r"\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")
        endfacet = re.compile(r"\s*endfacet\s+")
        loop = re.compile(r"\s*outer\s+loop\s+")
        endloop = re.compile(r"\s*endloop\s+")
        vertex = re.compile(r"\s*vertex" \
                + r"\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")

        current_line = 0
        facet_num = 0
        
        if True:
            for FACET in loaded_mesh.data:
                # All needed values now loaded for this facet
                #    proceed with processing
                current_vectors = loaded_mesh.vectors[facet_num]
                current_normal = loaded_mesh.normals[facet_num]
                facet_num += 1
                
                n = (FACET[0][0], FACET[0][1], FACET[0][2], 'v')
                p1 = (FACET[1][0][0], FACET[1][0][1], FACET[1][0][2])
                p2 = (FACET[1][1][0], FACET[1][1][1], FACET[1][1][2])
                p3 = (FACET[1][2][0], FACET[1][2][1], FACET[1][2][2])
                
                if p1 is None or p2 is None or p3 is None:
                    log.warn(("Invalid facet definition in line " \
                            + "%d of '%s'. Please validate the STL file!") \
                            % (current_line, filename))
                    n, p1, p2, p3 = None, None, None, None
                    
                if not n:
                    n = pnormalized(pcross(psub(p2, p1), psub(p3, p1)))
                
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
                                "line %d of '%s'. Please validate the STL " + \
                                "file!") % (current_line, filename))
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

        f2 = []
        for line in f2:
            if callback and callback():
                log.warn("STLImporter: load model operation cancelled")
                return None
            current_line += 1
            m = solid.match(line)
            if m:
                model.name = m.group(1)
                continue

            m = facet.match(line)
            if m:
                m = normal.match(line)
                if m:
                    n = (float(m.group('x')), float(m.group('y')), float(m.group('z')), 'v')
                else:
                    n = None
                continue
            m = loop.match(line)
            if m:
                continue
            m = vertex.match(line)
            if m:
                p = UniqueVertex(float(m.group('x')), float(m.group('y')),
                        float(m.group('z')))
                if p1 is None:
                    p1 = p
                elif p2 is None:
                    p2 = p
                elif p3 is None:
                    p3 = p
                else:
                    log.error("STLImporter: more then 3 points in facet " \
                            + "(line %d)" % current_line)
                continue
            m = endloop.match(line)
            if m:
                continue
            m = endfacet.match(line)
            if m:
                # All needed values now loaded for this facet
                #    proceed with processing
                current_vectors = loaded_mesh.vectors[facet_num]
                current_normal = loaded_mesh.normals[facet_num]
                facet_num += 1
                
                n = (current_normal[0], current_normal[1], current_normal[2], 'v')
                p1 = (current_vectors[0][0], current_vectors[0][1], current_vectors[0][2])
                p2 = (current_vectors[1][0], current_vectors[1][1], current_vectors[1][2])
                p3 = (current_vectors[2][0], current_vectors[2][1], current_vectors[2][2])
                
                if p1 is None or p2 is None or p3 is None:
                    log.warn(("Invalid facet definition in line " \
                            + "%d of '%s'. Please validate the STL file!") \
                            % (current_line, filename))
                    n, p1, p2, p3 = None, None, None, None
                    continue
                if not n:
                    n = pnormalized(pcross(psub(p2, p1), psub(p3, p1)))
                
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
                    print p1, p3, p2
                    print loaded_mesh.vectors[facet_num-1]
                    print
                elif dotcross < 0:
                    if not normal_conflict_warning_seen:
                        log.warn(("Inconsistent normal/vertices found in " + \
                                "line %d of '%s'. Please validate the STL " + \
                                "file!") % (current_line, filename))
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
                    continue
                n, p1, p2, p3 = (None, None, None, None)
                model.append(t)
                continue
            m = endsolid.match(line)
            if m:
                continue

    time_end = time.time()
    log.info("Imported STL model: %d vertices, %d edges, %d triangles in %.4f seconds." \
            % (vertices, edges, len(model.triangles()), time.time() - sTime))
    vertices = 0
    edges = 0
    kdtree = None

    if not model:
        # no valid items added to the model
        return None
    else:
        return model
    
