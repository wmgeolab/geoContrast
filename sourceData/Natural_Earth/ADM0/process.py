
import topojson as tp
import itertools
import os
import json

import shapefile as pyshp
from zipfile import ZipFile




#########

# autoset some params
SOURCE_NAME = 'Natural_Earth'
OUT_DIR = '../../../releaseData'
OUT_SOURCE_NAME = SOURCE_NAME
assert os.path.lexists(OUT_DIR)

# read source metadata
with open('sourceMetaData.json', encoding='utf8') as fobj:
    meta = json.load(fobj)

# procedures
def get_iso(feat):
    iso = feat['properties']['ADM0_A3']
    return iso

def iter_country_level_feats():
    fil = 'ne_10m_admin_0_countries.zip'
    archive = ZipFile(fil, 'r')
    shapefile = os.path.splitext(fil)[0] # root shapefile name
    # read file (pyshp)
    shp = archive.open(shapefile+'.shp')
    shx = archive.open(shapefile+'.shx')
    dbf = archive.open(shapefile+'.dbf')
    reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf)
    # get all country isos
    isos = set()
    for rec in reader.iterRecords():
        feat = {'properties': rec.as_dict()}
        iso = get_iso(feat)
        isos.add(iso)
    # loop countries
    for iso in sorted(isos):
        # yield country feats
        lvl = 'ADM0'
        feats = []
        for i,rec in enumerate(reader.iterRecords()):
            feat = {'type':'Feature', 'properties': rec.as_dict()}
            if get_iso(feat) == iso:
                geoj = reader.shape(i).__geo_interface__
                feat['geometry'] = geoj
                feats.append(feat)
        yield iso, lvl, feats

def get_adm_type(feat):
    typ = 'Unknown'
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
    typ = get_adm_type(feats[0]) # just doing the first one for now, although there may be multiple...

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




