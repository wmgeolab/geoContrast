
#import numpy as np
from ._delta import delta_encode

def arc_bbox(arc):
    xs,ys = zip(*arc)
    return min(xs),min(ys),max(xs),max(ys)

def bbox_union(*bboxes):
    xmins,ymins,xmaxs,ymaxs = zip(*bboxes)
    xmin,ymin,xmax,ymax = min(xmins),min(ymins),max(xmaxs),max(ymaxs)
    return xmin,ymin,xmax,ymax

def quantize(arc, kx, ky, xmin, ymin):
    # OLD/NOT USED
    quantized = []
    for x,y in arc:
        xnorm = int(round((x - xmin) / kx))
        ynorm = int(round((y - ymin) / ky))
        quantized.append((xnorm,ynorm))
    return quantized

def abs2rel(arc, scale=None, translate=None):
    """Yields delta-encoded coordinate tuples from an arc of absolute coordinates.

    If either the scale or translate parameter evaluate to False, yield the
    arc coordinates with no transformation."""
    # NOTE THAT scale HERE IS INVERSE OF WHAT'S STORED IN TOPOJSON transform.scale ATTR
    if scale and translate:
        # first coordinate is returned with transformation
        x, y = arc[0]
        a = int(round( (x-translate[0]) * scale[0] ))
        b = int(round( (y-translate[1]) * scale[1] ))
        yield a, b

        # subsequent coordinates are returned delta-encoded
        aprev,bprev = a,b
        for x, y in arc[1:]:
            # quantize
            a = int(round( (x-translate[0]) * scale[0] ))
            b = int(round( (y-translate[1]) * scale[1] ))
            # yield delta from previous
            da = a - aprev
            db = b - bprev
            yield da, db

            aprev,bprev = a,b
    
    else:
        for x,y in arc:
            yield x,y

def process_geometry(geometry, arcs):
    """
    Given an input GeoJSON geometry, add arc coordinates to the global list of arcs,
    and return a geometry object structure that references these arc indexes.
    """
    bboxes = []
    if geometry['type'] == 'Polygon':
        obj = []
        for ring in geometry['coordinates']:
            # each ring defined by a list of arc indexes
            # in our case only a single arc index
            i = len(arcs)
            obj.append( [i] )
            arcs.append( ring )
            bbox = arc_bbox(ring)
            bboxes.append(bbox)
    elif geometry['type'] == 'MultiPolygon':
        obj = []
        for poly in geometry['coordinates']:
            _poly = []
            for ring in poly:
                # each ring defined by a list of arc indexes
                # in our case only a single arc index
                i = len(arcs)
                _poly.append( [i] )
                arcs.append( ring )
                bbox = arc_bbox(ring)
                bboxes.append(bbox)
            obj.append(_poly)

    bbox = bbox_union(*bboxes)
    return obj, bbox

def topology(geojson, quantization=1e6):
    """
    Convert GeoJSON to TopoJSON.
    """
    layers = {}
    topo = {'type': 'Topology',
            'arcs': [],
            'objects': layers}

    # add arcs + objects
    layers['data'] = {'type':'GeometryCollection', 'geometries':[]}
    bboxes = []
    for feat in geojson['features']:
        geom = feat['geometry']
        arc_indexes, bbox = process_geometry(geom, topo['arcs'])
        obj = {'type': geom['type'], 
                'arcs': arc_indexes, # should be 'coordinates' if Multi/Point
                'properties': feat['properties'] # only if feature
                }
        layers['data']['geometries'].append(obj)
        bboxes.append(bbox)

    # add bbox
    topo['bbox'] = bbox = list(bbox_union(*bboxes))

    # quantize
    if quantization > 1:
        # compute and store quantization params
        minx,miny,maxx,maxy = bbox
        kx = (quantization - 1) / (maxx - minx) #(maxx - minx) / (quantization - 1)
        ky = (quantization - 1) / (maxy - miny) #(maxy - miny) / (quantization - 1)
        topo['transform'] = {
            'scale': [ 1 / kx, 1 / ky ],
            'translate': [ minx, miny ]
        }

        # quantize and delta encode
        for i,arc in enumerate(topo['arcs']):
            #quantized = np.int32(np.round((arc - (minx, miny)) / (kx, ky) * quantization))
            #print('c',len(arc),str(arc)[:1000])
            #arc_q = quantize(arc, kx, ky, minx, miny)
            #print('q',len(quantized),str(quantized)[:1000])
            #arc_q = delta_encode(arc_q)
            #print('d',len(delta_quantized),str(delta_quantized)[:1000])
            arc_q = list(abs2rel(arc, scale=(kx,ky), translate=topo['transform']['translate']))
            topo['arcs'][i] = arc_q # replace in-place

    return topo
