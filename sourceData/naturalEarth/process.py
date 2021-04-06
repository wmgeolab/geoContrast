
import topojson as tp
import itertools
import os
import json

# some params

OUT_DIR = '../../releaseData'
OUT_SOURCE_NAME = 'naturalEarth'
LICENSE = '?'
LICENSE_NOTES = '' 
LICENSE_SOURCE = 'https://www.naturalearthdata.com/about/terms-of-use/'
SOURCE_LINK = 'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/'
OTHER_NOTES = ''

SOURCE_YEAR = 2018 # year representative of
SOURCE_UPDATED = '2018-XX-XX'



#########

pth = 'ne_10m_admin_1_states_provinces.zip'

# read file (geopandas)
#import geopandas as gp
#dat = gp.read_file(pth)

# read file (pyshp)
import shapefile as pyshp
from zipfile import ZipFile
archive = ZipFile(pth, 'r')
shp = archive.open('ne_10m_admin_1_states_provinces.shp')
shx = archive.open('ne_10m_admin_1_states_provinces.shx')
dbf = archive.open('ne_10m_admin_1_states_provinces.dbf')
reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf)
print(reader)

# procedures

def get_iso(feat):
    iso = feat['properties']['adm0_a3']
    return iso

def get_adm_level(feat):
    return 'ADM1'

def get_adm_type(feat):
    typ = feat['properties']['type_en']
    return typ

##def get_date_start(feat):
##    pass
##
##def get_date_end(feat):
##    pass

def get_all_isos():
    isos = set()
    for rec in reader.iterRecords():
        feat = {'properties': rec.as_dict()}
        iso = get_iso(feat)
        isos.add(iso)
    return isos

def iter_country_feats(iso):
    for i,rec in enumerate(reader.iterRecords()):
        feat = {'type':'Feature', 'properties': rec.as_dict()}
        if get_iso(feat) == iso:
            geoj = reader.shape(i).__geo_interface__
            feat['geometry'] = geoj
            yield feat

# begin

# make dir
try: os.mkdir('{root}/{source}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME))
except: pass

# loop each country
for iso in sorted(get_all_isos()):
    print(iso)
    countryfeats = list(iter_country_feats(iso))

    # make sure folder exist
    try: os.mkdir('{root}/{source}/{iso}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso))
    except: pass
    
    # group by admin level
    for lvl,group in itertools.groupby(sorted(countryfeats, key=get_adm_level), key=get_adm_level):
        print('-->',lvl)
        
        # create topojson
        feats = [feat for feat in group]
##        topodata = tp.Topology(feats, prequantize=False).to_json()
##
##        # make sure folder exist
##        try: os.mkdir('{root}/{source}/{iso}/{lvl}'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl))
##        except: pass
##
##        # write topojson to file
##        dst = '{root}/{source}/{iso}/{lvl}/{source}_{iso}_{lvl}.topojson'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
##        with open(dst, 'w') as fobj:
##            fobj.write(topodata)

        # get dynamic metadata
        typ = get_adm_type(feats[0]) # just doing the first one for now, although there may be multiple...

        # write metadata to file
##        meta = { # wrong, this is the format used in the sourceData folder? 
##            'Boundary Representative of Year': 2018,
##            'ISO-3166-1 (Alpha-3)': iso,
##            'Boundary Type': lvl,
##            'Canonical Boundary Type Name': typ,
##            'Source 1': OUT_SOURCE_NAME,
##            'Source 2': '',
##            'Release Type': 'gbContrast',
##            'License': LICENSE,
##            'License Notes': LICENSE_NOTES,
##            'License Source': LICENSE_SOURCE,
##            'Link to Source Data': SOURCE_LINK,
##            'Other Notes': OTHER_NOTES,
##            }
        meta = {
            'boundaryID': None,
            'boundaryYear': SOURCE_YEAR,
            'boundaryISO': iso,
            'boundaryType': lvl,
            'boundaryCanonical': typ,
            'boundarySource-1': OUT_SOURCE_NAME,
            'boundarySource-2': '',
            'boundaryLicense': LICENSE,
            'licenseDetail': LICENSE_NOTES,
            'licenseSource': LICENSE_SOURCE,
            'boundarySourceURL': SOURCE_LINK,
            'downloadURL': '...',
            'sourceDataUpdateDate': SOURCE_UPDATED,
            #'buildUpdateDate': date.today.toisoformat(),
            }
        # TODO: rename so separated by dash, not underscore
        dst = '{root}/{source}/{iso}/{lvl}/{source}_{iso}_{lvl}_metaData.json'.format(root=OUT_DIR, source=OUT_SOURCE_NAME, iso=iso, lvl=lvl)
        with open(dst, 'w') as fobj:
            json.dump(meta, fobj)




