
import topojson as tp
import itertools
import os
import json

import shapefile as pyshp
from zipfile import ZipFile




#########

# autoset some params
SOURCE_NAME = os.path.split(os.path.abspath(''))[-1] # use name of current folder
SOURCE_FILES = ['ZMB_2017_01_01_SALB.zip/BNDA_ZMB_2017-01-01_present.shp']
OUT_DIR = '../../releaseData'
OUT_SOURCE_NAME = SOURCE_NAME

# custom procedures
def get_adm_type(feat):
    return 'Unknown'

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
    key = lambda f: f['properties'][dissolve_field]
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
    leveldefs = [{'level':2, 'dissolve_field':'ADM2NM', 'keep_fields':['ISO3CD','ADM1NM','SST1CD','ADM1CD','ADM2NM','SST2CD','ADM2CD']},
                 {'level':1, 'dissolve_field':'ADM1NM', 'keep_fields':['ISO3CD','ADM1NM','SST1CD','ADM1CD']},
                 {'level':0, 'dissolve_field':'ISO3CD', 'keep_fields':['ISO3CD']}
                 ]
    for leveldef in leveldefs:
        print(leveldef)
        
        # make sure admin level folder exist
        lvl = 'ADM{}'.format(int(leveldef['level']))
        try: os.mkdir('{root}/{source}/{iso}/{lvl}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl))
        except: pass

        # dissolve based on leveldef
        leveldef.pop('level')
        feats = dissolve_by(feats, **leveldef)
        print('dissolved to', len(feats), 'units')

        # create topojson
        feats = list(feats)
        topodata = tp.Topology(feats, prequantize=False).to_json()

        # write topojson to file
        dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}.topojson'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
        with open(dst, 'w', encoding='utf8') as fobj:
            fobj.write(topodata)

        # get dynamic metadata
        typ = get_adm_type(feats[0]) # just doing the first one for now, although there may be multiple...

        # update metadata
        overwrite_meta = {
            'boundaryType': lvl,
            'boundaryCanonical': typ,
            }
        meta.update(overwrite_meta)

        # write metadata to file
        dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}-metaData.json'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
        with open(dst, 'w', encoding='utf8') as fobj:
            json.dump(meta, fobj)




