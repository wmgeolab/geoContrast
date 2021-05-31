
import topojson as tp
import itertools
import os
import json

import shapefile as pyshp
from zipfile import ZipFile




#########

# autoset some params
SOURCE_NAME = os.path.split(os.path.abspath(''))[-1]
OUT_DIR = '../../releaseData'
OUT_SOURCE_NAME = SOURCE_NAME

# read source metadata
with open('sourceMetaData.json', encoding='utf8') as fobj:
    meta = json.load(fobj)

# procedures
def iter_country_level_feats():
    for fil in os.listdir('countryfiles'):
        iso = fil.replace('.zip','')
        archive = ZipFile('countryfiles/'+fil, 'r')
        shapefiles = [os.path.splitext(subfil)[0] # root shapefile names
                      for subfil in archive.namelist()
                      if subfil.endswith('.shp')]
        for shapefile in shapefiles:
            lvl = 'ADM' + shapefile[-1] # last char in filename
            # read file (pyshp)
            shp = archive.open(shapefile+'.shp')
            shx = archive.open(shapefile+'.shx')
            dbf = archive.open(shapefile+'.dbf')
            reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf)
            yield iso, lvl, reader.__geo_interface__['features']

def get_adm_type(feat, lvl):
    lvl_num = lvl[-1]
    if lvl_num == '0':
        typ = None
    else:
        typ = feat['properties']['ENGTYPE_'+lvl_num]
    return typ

# begin

# make dir
try: os.mkdir('{root}/{source}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME))
except: pass

# loop each country level group
for iso,lvl,feats in iter_country_level_feats():
    print(iso,lvl)

    # make sure iso folder exist
    try: os.mkdir('{root}/{source}/{iso}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso))
    except: pass

    # make sure admin level folder exist
    try: os.mkdir('{root}/{source}/{iso}/{lvl}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl))
    except: pass
    
    # create topojson
    feats = list(feats)
    #topodata = tp.Topology(feats, prequantize=False).to_json()

    # write topojson to file
    #dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}.topojson'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
    #with open(dst, 'w', encoding='utf8') as fobj:
    #    fobj.write(topodata)

    # get dynamic metadata
    typ = get_adm_type(feats[0], lvl) # just doing the first one for now, although there may be multiple...

    # update metadata
    overwrite_meta = {
        'boundaryISO': iso,
        'boundaryType': lvl,
        'boundaryCanonical': typ,
        }
    meta.update(overwrite_meta)

    # write metadata to file
    dst = '{root}/{source}/{iso}/{lvl}/{source}-{iso}-{lvl}-metaData.json'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
    with open(dst, 'w', encoding='utf8') as fobj:
        json.dump(meta, fobj)




