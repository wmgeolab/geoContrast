
import topojson as tp
import itertools
import os
import json

import shapefile as pyshp
from zipfile import ZipFile




#########

# autoset some params
SOURCE_NAME = 'CIV_CNTIG'
SOURCE_FILE = 'civ_admbnda_adm3_cntig_ocha_itos_20180706.zip'
OUT_DIR = '../../../releaseData'
OUT_SOURCE_NAME = SOURCE_NAME

# custom procedures
def get_adm_type(feat):
    return None

# standard procedures
def load_feats(path):
    # for now must be path to a zipfile containing a single shapefile
    archive = ZipFile(path, 'r')
    shapefiles = [os.path.splitext(subfil)[0] # root shapefile names
                  for subfil in archive.namelist()
                  if subfil.endswith('.shp')]
    assert len(shapefiles) == 1
    shapefile = shapefiles[0]
    # read file (pyshp)
    shp = archive.open(shapefile+'.shp')
    shx = archive.open(shapefile+'.shx')
    dbf = archive.open(shapefile+'.dbf')
    reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf)
    return reader.__geo_interface__['features']

# begin

# read source metadata
with open('sourceMetaData.json') as fobj:
    meta = json.load(fobj)

# make dir
try: os.mkdir('{root}/{source}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME))
except: pass

# load shapefile
feats = load_feats(SOURCE_FILE)

# make sure iso folder exist
iso = meta['boundaryISO']
try: os.mkdir('{root}/{source}/{iso}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso))
except: pass

# make sure admin level folder exist
lvl = meta['boundaryType']
try: os.mkdir('{root}/{source}/{iso}/{lvl}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl))
except: pass

# create topojson
feats = list(feats)
topodata = tp.Topology(feats, prequantize=False).to_json()

# write topojson to file
dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}.topojson'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
with open(dst, 'w') as fobj:
    fobj.write(topodata)

# get dynamic metadata
typ = get_adm_type(feats[0]) # just doing the first one for now, although there may be multiple...

# update metadata
overwrite_meta = {
    'boundaryCanonical': typ,
    }
meta.update(overwrite_meta)

# write metadata to file
dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}-metaData.json'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
with open(dst, 'w') as fobj:
    json.dump(meta, fobj)




