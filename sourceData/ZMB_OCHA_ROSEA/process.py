
import topojson as tp
import itertools
import os
import json

import shapefile as pyshp
from zipfile import ZipFile




#########

# autoset some params
SOURCE_NAME = os.path.split(os.path.abspath(''))[-1] # use name of current folder
SOURCE_FILES = ['zmb_adm_dmmu_20201124_shp.zip/Shapefiles/zmb_admbnda_adm0_dmmu_20201124.shp',
                'zmb_adm_dmmu_20201124_shp.zip/Shapefiles/zmb_admbnda_adm1_dmmu_20201124.shp',
                'zmb_adm_dmmu_20201124_shp.zip/Shapefiles/zmb_admbnda_adm2_dmmu_20201124.shp']
OUT_DIR = '../../releaseData'
OUT_SOURCE_NAME = SOURCE_NAME

# custom procedures
def get_level(filename):
    num = filename.split('_')[-3][-1]
    assert num.isnumeric()
    return 'ADM'+num
    
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

    # make sure iso folder exist
    iso = meta['boundaryISO']
    try: os.mkdir('{root}/{source}/{iso}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso))
    except: pass

    # make sure admin level folder exist
    lvl = get_level(SOURCE_FILE)
    try: os.mkdir('{root}/{source}/{iso}/{lvl}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl))
    except: pass

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



