'''
Def import_data()
    Args:
•	path_to_shp
•	[output_dir]
•	Iso
•	Iso_field
•	Iso_path
•	Level
•	Level_field
•	Level_path
•	Type
•	Type_field (either a field name, or a conditional dict of level-field pairs)
•	Year
•	Year_field
•	Name_field (either a field name, or a conditional dict of level-field pairs)
•	Source
•	Download
•	License
•	Dissolve_by
•	Keep_fields

The output is a topojson file and a meta file located in the output_dir.
(Our auto script will simply loop each source folder and use the same name in a target root folder)

A meta.txt file contains a json dict of all these args which defines how to import a single data file. 

For importing from a large number of data files where some of the args are defined by the path/file names,
the path arg allows either a list of pathnames or regex style wildcards in order to loop through folder
structures, and the «*_path» args uses regex to extract the arg from each pathname. 

For importing from several data files using args that need to be custom specified for each, the meta file
can also contain a json list of one or more such dicts. Args that stay the same dont have to be repeated
after the first dict. 

Lower admin levels can be derived from higher levels by specifying a list of json dicts referencing the same
file, where each dict specifies a different level, type, dissolve_field, and keep_fields. 
'''

#import topojson as tp
import topojson_simple
import itertools
import os
import json
import re
import csv
import warnings

import shapefile as pyshp
from zipfile import ZipFile, ZIP_DEFLATED

# create iso lookup dict
iso2_to_3 = {}
filedir = os.path.dirname(__file__)
with open(os.path.join(filedir, 'buildData/countries_codes_and_coordinates.csv'), encoding='utf8', newline='') as f:
    csvreader = csv.DictReader(f)
    for row in csvreader:
        iso2 = row['Alpha-2 code'].strip().strip('"')
        iso3 = row['Alpha-3 code'].strip().strip('"')
        iso2_to_3[iso2] = iso3

def get_reader(path, encoding='utf8'):
    # for now must be path to a shapefile within a zipfile
    zpath,shapefile = path[:path.find('.zip')+4], path[path.find('.zip')+4+1:]
    archive = ZipFile(zpath, 'r')
    shapefile = os.path.splitext(shapefile)[0] # root shapefile name
    # read file (pyshp)
    shp = archive.open(shapefile+'.shp')
    shx = archive.open(shapefile+'.shx')
    dbf = archive.open(shapefile+'.dbf')
    reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf, encoding=encoding)
    return reader

def inspect_data(path, numrows=3):
    if path.endswith('.zip'):
        # inspect all shapefiles inside zipfile
        archive = ZipFile(path, 'r')
        paths = [os.path.join(path, name)
                 for name in archive.namelist()
                 if name.endswith('.shp')]
    else:
        # inspect the specified zipfile member
        paths = [path]
    # inspect each file
    for path in paths:
        print('')
        print(path)
        reader = get_reader(path)
        for i,rec in enumerate(reader.iterRecords()):
            print(json.dumps(rec.as_dict(date_strings=True), sort_keys=True, indent=4))
            if i >= (numrows-1):
                break

def import_data(input_dir,
                input_path,
                output_dir,
                collection,
                
                collection_subset=None,
                
                iso=None,
                iso_field=None,
                iso_path=None,
                level=None,
                level_field=None,
                level_path=None,
                type=None,
                type_field=None,
                year=None,
                year_field=None,
                
                name_field=None,
                source=None,
                source_updated=None,
                source_url=None,
                download_url=None,
                license=None,
                license_detail=None,
                license_url=None,
                note=None,
                
                dissolve=False,
                keep_fields=None,
                drop_fields=None,

                encoding='utf8',

                write_meta=True,
                write_stats=True,
                write_data=True,
                ):

    # define standard procedures
    
    def iter_paths(input_dir, input_path):
        # NOTE: input_path is relative to input_dir
        # this function returns the absolute path by joining them
        # ... 
        # path can be a single path, a path with regex wildcards, or list of paths
        if isinstance(input_path, str):
            if '*' in input_path:
                # regex
                pattern = input_path.replace('\\', '/')
                pattern = pattern.replace('*', '[^/]*')
                #raise Exception('Need to generalize this manual hardcoding for gadm...') # see next line
                zip_pattern = pattern.split('.zip')[0] + '.zip'
                print('regex', zip_pattern, pattern)
                for dirpath,dirnames,filenames in os.walk(os.path.abspath(input_dir)):
                    for filename in filenames:
                        zpath = os.path.join(dirpath, filename)
                        zpath = zpath.replace('\\', '/')
                        #print(zpath)
                        if re.search(zip_pattern, zpath):
                            #print('ZIPFILE MATCH')
                            archive = ZipFile(zpath, 'r')
                            for zmember in archive.namelist():
                                pth = os.path.join(zpath, zmember)
                                pth = pth.replace('\\', '/')
                                if re.search(pattern, pth):
                                    #print('ZIPFILE MEMBER MATCH')
                                    yield pth
            else:
                # single path
                yield os.path.join(input_dir, input_path)
                
        elif isinstance(input_path, list):
            # list of paths
            for pth in input_path:
                yield os.path.join(input_dir, pth)

    def iter_country_level_feats(reader, path,
                                 iso=None, iso_field=None, iso_path=None,
                                 level=None, level_field=None, level_path=None,
                                 load_geometries=True):
        # determine static iso
        if iso is None and iso_path:
            # need to determine iso
            #iso = regex(path)
            raise NotImplementedError()

        # determine static level
        if level is None and level_path:
            # need to determine level
            #level = regex(path)
            raise NotImplementedError()

        ##### 

        # define how to iterate isos
        if iso is not None:
            # a single iso
            if len(iso) == 2:
                if iso in iso2_to_3:
                    iso = iso2_to_3[iso]
                else:
                    raise Exception("Unable to lookup 2-digit iso code '{}'.".format(iso))
                
            if len(iso) != 3 or not iso.isalpha():
                raise Exception("Country iso value must consist of 3 alphabetic characters, not '{}'.".format(iso))

            def iter_country_recs():
                yield iso, reader.records()
        else:
            # isos defined by a field
            if iso_field is None:
                raise Exception('Requires either iso, iso_path, or iso_field args')

            def iter_country_recs():
                # memory friendly but slow
                
                # loop and get all isos
                #isos = set((rec[iso_field] for rec in reader.iterRecords()))
                #isos = sorted(isos)

                # loop each iso and get relevant features
                #for iso in isos:
                #    countryrecs = []
                #    for rec in reader.iterRecords():
                #        if rec[iso_field] == iso:
                #            countryrecs.append(rec)
                #    yield iso, countryrecs

                # more efficient
                key = lambda rec: rec[iso_field]
                for iso,countryrecs in itertools.groupby(sorted(reader.records(), key=key), key=key):
                    if len(iso) == 2:
                        if iso in iso2_to_3:
                            iso = iso2_to_3[iso]
                        else:
                            warnings.warn("Skipping country iso '{}': unable to lookup 2-digit iso code.".format(iso))
                            continue
                    if len(iso) != 3 or not iso.isalpha():
                        warnings.warn("Skipping country iso '{}': iso value must consist of 3 alphabetic characters.".format(iso))
                        continue
                    yield iso, list(countryrecs)

        for iso, countryrecs in iter_country_recs():
            # define how to iterate levels
            if level is not None:
                # a single level
                def iter_level_recs():
                    yield level, countryrecs
            else:
                # levels defined by a field
                if level_field is None:
                    raise Exception('Requires either level, level_path, or level_field args')

                def iter_level_recs():
                    # loop and get all levels
                    levels = set((rec[level_field] for rec in countryrecs))
                    levels = sorted(levels)

                    # loop each level and get relevant features
                    for level in levels:
                        levelrecs = []
                        for rec in countryrecs:
                            if rec[level_field] == level:
                                levelrecs.append(rec)
                        yield level, levelrecs

            # loop each level and return relevant features as geojson
            for level,levelrecs in iter_level_recs():
                print('loading data') # this will be the most time consuming part (loading geometries)
                countrylevelfeats = []
                for rec in levelrecs:
                    props = rec.as_dict(date_strings=True)
                    if load_geometries is True:
                        geoj = reader.shape(rec.oid).__geo_interface__
                        if geoj is None or not geoj['coordinates']:
                            # skip over null geometries or geometries with zero coords
                            continue
                    else:
                        geoj = None
                    feat = {'type':'Feature', 'properties':props, 'geometry':geoj}
                    countrylevelfeats.append(feat)
                yield iso, level, countrylevelfeats


    def dissolve_by(feats, dissolve_field, keep_fields=None, drop_fields=None):
        from shapely.geometry import asShape
        from shapely.ops import cascaded_union
        if isinstance(dissolve_field, str):
            key = lambda f: f['properties'][dissolve_field]
        elif isinstance(dissolve_field, list):
            key = lambda f: [f['properties'][subkey] for subkey in dissolve_field]
        elif dissolve_field:
            key = lambda f: 'dummy'
        newfeats = []
        for val,group in itertools.groupby(sorted(feats, key=key), key=key):
            group = list(group)
            print('dissolving',val,len(group))
            # dissolve into one geometry
            if len(group) > 1:
                geoms = [asShape(feat['geometry']) for feat in group]
                geoms = [geom.buffer(1e-7) for geom in geoms] # fill in gaps of approx 10mm, topology will later snap together overlaps when quantizing to 100mm
                dissolved = cascaded_union(geoms)
                # attempt to fix invalid result
                if not dissolved.is_valid:
                    dissolved = dissolved.buffer(0)
                dissolved_geoj = dissolved.__geo_interface__
            else:
                dissolved_geoj = group[0]['geometry']
            
            # which properties to keep
            allprops = group[0]['properties']
            if drop_fields:
                keep_fields = [field for field in allprops.keys() if field not in drop_fields]
            if keep_fields:
                newprops = dict([(field,allprops[field]) for field in keep_fields])
            else:
                newprops = allprops
            # create and add feat
            feat = {'type':'Feature', 'properties':newprops, 'geometry':dissolved_geoj}
            newfeats.append(feat)
        return newfeats

    # make dir
    try: os.mkdir('{output}'.format(output=output_dir))
    except: pass
    try: os.mkdir('{output}/{collection}'.format(output=output_dir, collection=collection))
    except: pass

    # prep source list
    sources = source if isinstance(source, list) else [source]

    # loop input files
    iter_kwargs = {'iso':iso,
                   'iso_field':iso_field,
                   'iso_path':iso_path,
                   'level':level,
                   'level_field':level_field,
                   'level_path':level_path,
                   'load_geometries':write_data or write_stats}
    for path in iter_paths(input_dir, input_path):
        print('')
        print(path)

        # load shapefile
        reader = get_reader(path, encoding)

        # iter country-levels
        for iso,level,feats in iter_country_level_feats(reader, path,
                                                        **iter_kwargs):
            print('')
            print('{}-ADM{}:'.format(iso, level), len(feats), 'admin units')

            # make sure iso folder exist
            try: os.mkdir('{output}/{collection}/{iso}'.format(output=output_dir, collection=collection, iso=iso))
            except: pass

            # make sure admin level folder exist
            try: os.mkdir('{output}/{collection}/{iso}/ADM{lvl}'.format(output=output_dir, collection=collection, iso=iso, lvl=level))
            except: pass

            # get type info
            if type is None:
                if type_field:
                    type = feats[0]['properties'][type_field] # for now just use the type of the first feature
            if not type:
                type = 'Unknown'

            # get year info
            if year is None:
                if year_field:
                    year = feats[0]['properties'][year_field] # for now just use the year of the first feature
            if not year:
                year = 'Unknown'

            # dissolve if specified
            if (write_data is True or write_stats is True) and dissolve:
                feats = dissolve_by(feats, dissolve, keep_fields, drop_fields)
                print('dissolved to', len(feats), 'admin units')

            # check that name_field is correct
            if name_field is not None:
                fields = feats[0]['properties'].keys()
                if name_field not in fields:
                    raise Exception("name_field arg '{}' is not a valid field; must be one of: {}".format(name_field, fields))

            # determine dataset name, in case multiple datasets (folders) inside folder
            dataset = collection
            if collection_subset:
                dataset += '_' + collection_subset

            # write data
            if write_data:
                print('writing data')

                # write geojson to zipfile
                # MAYBE ALSO ROUND TO 1e6, SHOULD DECR FILESIZE
                #zip_path = '{output}/{collection}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}-geojson.zip'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                #with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED) as archive:
                #    filename = '{dataset}-{iso}-ADM{lvl}.geojson'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                #    geoj = {'type':'FeatureCollection', 'features':feats}
                #    geoj_string = json.dumps(geoj)
                #    archive.writestr(filename, geoj_string)
                
                # create topology quantized to 1e6 (10cm) and delta encoded, greatly reduces filesize
                
                # NOTE: quantization isn't always the same as precision since it depends on the topology bounds
                # in some cases like USA (prob due to large extent?), precision degrades 3 decimals
                # INSTEAD added a custom precision arg to explicitly set decimal precision
                
                #if len(feats) == 1:
                #    print('only 1 object, creating topojson without topology')
                #    topo = tp.Topology(feats, topology=False, prequantize=1e6)
                #elif len(feats) > 1:
                #    try:
                #        print('> 1 objects, creating topojson with topology')
                #        topo = tp.Topology(feats, topology=True, prequantize=1e6)
                #    except:
                #        print('!!! failed to compute topology, creating topojson without topology')
                #        topo = tp.Topology(feats, topology=False, prequantize=1e6)
                print('creating quantized topojson (no topology optimization)')
                #topo = tp.Topology(feats, topology=False, prequantize=1e6)
                topo = topojson_simple.encode.topology({'features':feats}, precision=6)

                print('outputting to json')
                #topodata = topo.to_json()
                topodata = json.dumps(topo)

                # write topojson to zipfile
                zip_path = '{output}/{collection}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}.topojson.zip'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                filename = '{dataset}-{iso}-ADM{lvl}.topojson'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                # check if has changed
                print('checking if data exists and has changed')
                has_changed = False
                if os.path.lexists(zip_path):
                    with ZipFile(zip_path, mode='r') as archive:
                        with archive.open(filename, mode='r') as fobj:
                            # compare encoded topojson string with zipfile topojson string
                            # note that python writes json strings as unicode escaped ascii, rather than utf8 encoded
                            topodata_old = fobj.read().decode('ascii')
                            assert (isinstance(topodata, str) and isinstance(topodata_old, str))
                            if topodata != topodata_old:
                                has_changed = True
                else:
                    has_changed = True
                # write if changed
                if has_changed:
                    print('writing to file')
                    with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED) as archive:
                        archive.writestr(filename, topodata)

            # update metadata
            meta = {
                    "boundaryYearRepresented": year,
                    "boundaryISO": iso,
                    "boundaryType": 'ADM{}'.format(int(level)),
                    "boundaryCanonical": type,
                    "boundaryLicense": license,
                    "nameField": name_field,
                    "licenseDetail": license_detail,
                    "licenseSource": license_url,
                    "boundarySourceURL": source_url,
                    "sourceDataUpdateDate": source_updated,
                    }
            for i,source in enumerate(sources):
                meta['boundarySource-{}'.format(i+1)] = source
            if note:
                meta['note'] = note

            # write metadata to file
            if write_meta is True:
                print('writing meta', meta)
                dst = '{output}/{collection}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}-metaData.json'.format(output=output_dir, collection=collection, dataset=dataset, iso=iso, lvl=level)
                with open(dst, 'w', encoding='utf8') as fobj:
                    json.dump(meta, fobj, indent=4)

            # calc and output boundary stats
            if write_stats is True:
                print('writing stats')
                stats = calc_stats(feats)
                print(stats)
                dst = '{output}/{collection}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}-stats.json'.format(output=output_dir, collection=collection, dataset=dataset, iso=iso, lvl=level)
                with open(dst, 'w', encoding='utf8') as fobj:
                    json.dump(stats, fobj, indent=4)

_geod = None

def get_pyproj_geod():
    global _geod
    if _geod is None:
        # only create the geod once in case of overhead
        from pyproj import Geod
        _geod = Geod(ellps="WGS84")
    return _geod

def geojson_area_perimeter(geoj):
    # area may be negative if incorrect orientation
    # but the abs(area) will be correct as long as ext and holes
    # have opposite orientation
    import numpy as np
    geod = get_pyproj_geod()
    
    if geoj['type'] == 'MultiPolygon':
        polys = geoj['coordinates']
    elif geoj['type'] == 'Polygon':
        polys = [geoj['coordinates']]
        
    area = 0
    perim = 0
    for poly in polys:
        for ring in poly:
            coords = np.array(ring)
            lons,lats = coords[:,0],coords[:,1]
            _area,_perim = geod.polygon_area_perimeter(lons, lats)
            area += _area
            perim += _perim
    return area, perim

def calc_stats(feats):
    stats = {}
    # unit count
    stats['boundaryCount'] = len(feats)
    # vertices, area, and perimiter
    #from shapely.geometry import asShape
    area = 0
    perim = 0
    verts = 0
    for feat in feats:
        # geodesy

        # pyproj
        # pyproj shapely version
        #geom = asShape(feat['geometry'])
        #geod = get_pyproj_geod()
        #_area, _perim = geod.geometry_area_perimeter(geom)
        # pyproj geojson version, much faster
        _area, _perim = geojson_area_perimeter(feat['geometry'])

        # some faster alternatives that avoids pyproj? 
        # https://stackoverflow.com/questions/6656475/python-speeding-up-geographic-comparison
        # https://github.com/geospace-code/pymap3d
        # https://github.com/actushumanus/nphaversine
        # https://github.com/qyliu-hkust/fasthaversine
        # https://github.com/yandex/mapsapi-area
        # https://github.com/Turfjs/turf/blob/master/packages/turf-area/index.ts

        area += _area
        perim += _perim
        
        # verts
        _verts = 0
        if feat['geometry']['type'] == 'MultiPolygon':
            polys = feat['geometry']['coordinates']
        elif feat['geometry']['type'] == 'Polygon':
            polys = [feat['geometry']['coordinates']]
        for poly in polys:
            for ring in poly:
                _verts += len(ring)
        verts += _verts
    area = abs(area) / 1000000 # convert m2 to km2 + fix pyproj which treats ccw as positive area (opposite of geojson)
    perim = perim / 1000 # convert m to km
    stats['statsArea'] = area
    stats['statsPerimeter'] = perim
    stats['statsVertices'] = verts
    # line resolution
    stats['statsLineResolution'] = (perim * 1000) / verts # meters between vertices
    stats['statsVertexDensity'] = verts / perim # vertices per km
    return stats



