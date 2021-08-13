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

import topojson as tp
import itertools
import os
import json
import re

import shapefile as pyshp
from zipfile import ZipFile

def get_reader(path):
    # for now must be path to a shapefile within a zipfile
    zpath,shapefile = path[:path.find('.zip')+4], path[path.find('.zip')+4+1:]
    archive = ZipFile(zpath, 'r')
    shapefile = os.path.splitext(shapefile)[0] # root shapefile name
    # read file (pyshp)
    shp = archive.open(shapefile+'.shp')
    shx = archive.open(shapefile+'.shx')
    dbf = archive.open(shapefile+'.dbf')
    reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf)
    return reader

def inspect_data(path):
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
            if i >= 2:
                break

def import_data(input_dir,
                input_path,
                output_dir,
                data_name,
                
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
                
                dissolve_field=None,
                keep_fields=None,

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
                zip_pattern = 'countryfiles' #pattern.split('.zip')[0] + '.zip'
                #print('regex', zip_pattern, pattern)
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
            if len(iso) != 3 or not iso.isalpha():
                raise Exception("Country iso value must consist of 3 alphabetic characters, not '{}'.".format(iso))

            def iter_country_recs():
                yield iso, reader.records()
        else:
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
                    if len(iso) != 3 or not iso.isalpha():
                        warnings.warn("Skipping country iso '{}': iso value must consist of 3 alphabetic characters.".format(iso))
                        continue
                    yield iso, list(countryrecs)

        for iso, countryrecs in iter_country_recs():
            # define how to iterate levels
            if level is not None:
                def iter_level_recs():
                    yield level, countryrecs
            else:
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
                countrylevelfeats = []
                for rec in levelrecs:
                    props = rec.as_dict(date_strings=True)
                    if load_geometries is True:
                        geoj = reader.shape(rec.oid).__geo_interface__
                    else:
                        geoj = None
                    feat = {'type':'Feature', 'properties':props, 'geometry':geoj}
                    countrylevelfeats.append(feat)
                yield iso, level, countrylevelfeats


    def dissolve_by(feats, dissolve_field, keep_fields):
        from shapely.geometry import asShape
        from shapely.ops import cascaded_union
        key = lambda f: f['properties'][dissolve_field] if dissolve_field else 'dummy'
        newfeats = []
        for val,group in itertools.groupby(sorted(feats, key=key), key=key):
            group = list(group)
            print(val,len(group))
            # dissolve into one geometry
            if len(group) > 1:
                geoms = [asShape(feat['geometry']) for feat in group]
                dissolved = cascaded_union(geoms)
                dissolved_geoj = dissolved.__geo_interface__
            else:
                dissolved_geoj = group[0]['geometry']
                dissolved = asShape(dissolved_geoj)
            # attempt to fix invalid result
            if not dissolved.is_valid:
                dissolved_geoj = dissolved.buffer(0).__geo_interface__
            # which properties to keep
            allprops = group[0]['properties']
            newprops = dict([(field,allprops[field]) for field in keep_fields])
            # create and add feat
            feat = {'type':'Feature', 'properties':newprops, 'geometry':dissolved_geoj}
            newfeats.append(feat)
        return newfeats

    # make dir
    try: os.mkdir('{output}/{dataset}'.format(output=output_dir, dataset=data_name))
    except: pass

    # loop source files
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
        reader = get_reader(path)

        # iter country-levels
        for iso,level,feats in iter_country_level_feats(reader, path,
                                                        **iter_kwargs):
            print('')
            print('{}-ADM{}:'.format(iso, level), len(feats), 'admin units')

            # make sure iso folder exist
            try: os.mkdir('{output}/{dataset}/{iso}'.format(output=output_dir, dataset=data_name, iso=iso))
            except: pass

            # make sure admin level folder exist
            try: os.mkdir('{output}/{dataset}/{iso}/ADM{lvl}'.format(output=output_dir, dataset=data_name, iso=iso, lvl=level))
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
            if dissolve_field:
                #feats = dissolve_by(feats, dissolve_field, keep_fields)
                #print('dissolved to', len(feats), 'units')
                raise NotImplementedError()

            # check that name_field is correct
            if name_field is not None:
                fields = feats[0]['properties'].keys()
                if name_field not in fields:
                    raise Exception("name_field arg '{}' is not a valid field; must be one of: {}".format(name_field, fields))

            # write data
            if write_data:
                print('writing data')
                
                # create topojson
                topodata = tp.Topology(feats, prequantize=False).to_json()

                # write topojson to file
                dst = '{output}/{dataset}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}.topojson'.format(output=output_dir, dataset=data_name, iso=iso, lvl=level)
                with open(dst, 'w', encoding='utf8') as fobj:
                    fobj.write(topodata)

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
                    "downloadURL": download_url,
                    "sourceDataUpdateDate": source_updated,
                    }
            sources = source if isinstance(source, list) else [source]
            for i,source in enumerate(sources):
                meta['boundarySource-{}'.format(i+1)] = source

            # write metadata to file
            if write_meta is True:
                print('writing meta', meta)
                dst = '{output}/{dataset}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}-metaData.json'.format(output=output_dir, dataset=data_name, iso=iso, lvl=level)
                with open(dst, 'w', encoding='utf8') as fobj:
                    json.dump(meta, fobj, indent=4)

            # calc and output boundary stats
            if write_stats is True:
                stats = calc_stats(feats, meta)
                print('writing stats', stats)
                dst = '{output}/{dataset}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}-stats.json'.format(output=output_dir, dataset=data_name, iso=iso, lvl=level)
                with open(dst, 'w', encoding='utf8') as fobj:
                    json.dump(stats, fobj, indent=4)

def calc_stats(feats, meta):
    stats = {}
    # unit count
    stats['boundaryCount'] = len(feats)
    # source year lag
    yr = meta['boundaryYearRepresented']
    updated = meta['sourceDataUpdateDate']
    updated_year_match = re.search('([0-9]{4})', updated)
    if yr == 'Unknown' or updated_year_match is None:
        stats['boundaryYearSourceLag'] = None
    else:
        stats['boundaryYearSourceLag'] = int(float(updated_year_match.group())) - yr
    # vertices, area, and perimiter
    from shapely.geometry import asShape
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    area = 0
    perim = 0
    verts = 0
    for feat in feats:
        # geodesy
        geom = asShape(feat['geometry'])
        _area, _perim = geod.geometry_area_perimeter(geom)
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
    area = abs(area / 1000000) # convert m2 to km2 + fix pyproj which treats ccw as positive area (opposite of geojson)
    perim = perim / 1000 # convert m to km
    stats['statsArea'] = area
    stats['statsPerimeter'] = perim
    stats['statsVertices'] = verts
    # line resolution
    stats['statsLineResolution'] = (perim * 1000) / verts # meters between vertices
    stats['statsVertexDensity'] = verts / perim # vertices per km
    return stats



