
import topojson as tp
import itertools
import os
import json

import shapefile as pyshp
from zipfile import ZipFile




#########

# autoset some params
SOURCE_NAME = os.path.split(os.path.abspath(''))[-1] # use name of current folder
SOURCE_FILES = ['GRID3_Zambia_-_Administrative_Boundaries_Districts_2020.zip/GRID3_Zambia_-_Administrative_Boundaries_Districts_2020.shp']
OUT_DIR = '../../releaseData'
OUT_SOURCE_NAME = SOURCE_NAME

#######################

# begin

# define standard procedures
def load_feats(path):
    # for now must be path to a shapefile within a zipfile
    zpath,shapefile = path[:path.find('.zip')+4], path[path.find('.zip')+4+1:]
    archive = ZipFile(zpath, 'r')
    shapefile = os.path.splitext(shapefile)[0] # root shapefile name
    # read file (pyshp)
    shp = archive.open(shapefile+'.shp')
    shx = archive.open(shapefile+'.shx')
    dbf = archive.open(shapefile+'.dbf')
    reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf)
    return reader.__geo_interface__['features']

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

# read source metadata
with open('sourceMetaData.json', encoding='utf8') as fobj:
    meta = json.load(fobj)

# make dir
try: os.mkdir('{root}/{source}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME))
except: pass

# loop source files
for SOURCE_FILE in SOURCE_FILES:
    print(SOURCE_FILE)

    # load shapefile
    feats = load_feats(SOURCE_FILE)
    print('originally', len(feats), 'admin units')

    # make sure iso folder exist
    iso = meta['boundaryISO']
    try: os.mkdir('{root}/{source}/{iso}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso))
    except: pass

    # loop admin levels and collapse
    leveldefs = [{'level':2, 'type':'Province', 'dissolve_field':'DISTRICT', 'keep_fields':'FID Shape_Leng Shape_Area FEATURE_TY PROVINCE Area_km PROV_CODE DIST_CODE DISTRICT Shape__Are Shape__Len'.split()},
                 {'level':1, 'type':'District', 'dissolve_field':'PROVINCE', 'keep_fields':'PROVINCE PROV_CODE'.split()},
                 {'level':0, 'type':'Country', 'dissolve_field':None, 'keep_fields':[]}
                 ]
    for leveldef in leveldefs:
        print(leveldef)

        # get misc metadata
        lvl = 'ADM{}'.format(int(leveldef['level']))
        typ = leveldef.get('type', 'Unknown')
        
        # make sure admin level folder exist
        try: os.mkdir('{root}/{source}/{iso}/{lvl}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl))
        except: pass

        # dissolve based on leveldef
        leveldef.pop('level')
        leveldef.pop('type', None)
        feats = dissolve_by(feats, **leveldef)
        print('dissolved to', len(feats), 'units')

        # create topojson
        feats = list(feats)
        topodata = tp.Topology(feats, prequantize=False).to_json()

        # write topojson to file
        dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}.topojson'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
        with open(dst, 'w', encoding='utf8') as fobj:
            fobj.write(topodata)

        # update metadata
        overwrite_meta = {
            'boundaryType': lvl,
            'boundaryCanonical': typ,
            }
        newmeta = meta.copy()
        newmeta.update(overwrite_meta)

        # write metadata to file
        dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}-metaData.json'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
        with open(dst, 'w', encoding='utf8') as fobj:
            json.dump(newmeta, fobj)




