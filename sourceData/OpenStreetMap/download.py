
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from zipfile import ZipFile, ZIP_DEFLATED
import tempfile
import os
import io
import itertools
import json
import gzip
import shapefile
import traceback

# params
api_key = input('Please input your personal api key from osm-boundaries.com (see "API url" under the "Download" window):\n >>> ')
db_date = '2021-07-12' # check osm-boundaries.com for latest build date
ignore_isos = ['CAN','CHL','FRA','USA']

# get all iso osm ids
print('list of isos:')
url = 'https://raw.githubusercontent.com/simonepri/osm-countries/master/osm.json'
osmcodes = json.loads(urlopen(url).read().decode('utf8'))

# loop isos and download+unzip each
print('downloading:')
for iso,osmid in osmcodes.items():
    print('')
    print(iso,osmid)
    if os.path.lexists(iso):
        print('folder already exists, skipping')
        continue
    if iso in ignore_isos:
        print('ignoring iso')
        continue

    yr,mn,dy = db_date.split('-')
    db = 'osm{}{}{}'.format(yr,mn,dy)
    params = {'apiKey':api_key,
              'db':db,
              'osmIds':'-'+osmid,
              'format':'GeoJSON',
              }
    paramstring = urlencode(params)
    paramstring += '&recursive&landOnly' #&includeAllTags'
    url = 'https://osm-boundaries.com/Download/Submit?{}'.format(paramstring)
    
    print('downloading from',url)
    req = Request(url, 
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'},
                )
    try:
        resp = urlopen(req)
    except:
        print('ERROR:', traceback.format_exc())
        continue

    print('extracting from gzip')
    with gzip.open(resp, 'rb') as f:
        geoj = json.loads(f.read().decode('utf8'))
    #print(str(geoj)[:1000])

    # make folder and output zipfile
    try: os.mkdir(iso)
    except: pass
    zip_path = '{iso}/{iso}.zip'.format(iso=iso)
    with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED) as archive:

        print('iterating admin levels')
        # AUTO INCR EACH LEVEL AND EXPORT TO SEPARATE SHAPEFILE
        admin_feats = [feat for feat in geoj['features']
                        if feat['properties']['boundary'] == 'administrative'
                        and feat['properties']['admin_level']
                        and feat['geometry']['coordinates']
                        ]
        key = lambda feat: feat['properties']['admin_level']
        inputs = []
        adm_lvl = 0
        for osm_lvl,feats in itertools.groupby(sorted(admin_feats, key=key), key=key):
            feats = list(feats)
            print('# level',osm_lvl,'count',len(feats))
            
            print('converting to shapefile')
            def calc_charfieldsize(feats, field):
                size = 0
                for feat in feats:
                    val = feat['properties'][field]
                    if not isinstance(val, str):
                        val = str(val)
                    enc = val.encode('utf8')
                    size = max(size, len(enc))
                return size
            shapefile_path = os.path.join(tempfile.gettempdir(), 'osm-boundary-converted')
            with shapefile.Writer(shapefile_path, encoding='utf8') as writer:
                fields = list(feats[0]['properties'].keys())
                for field in fields:
                    size = calc_charfieldsize(feats, field)
                    print(field, size)
                    writer.field(field, 'C', size)
                for feat in feats:
                    #print(feat['properties'])
                    writer.record(**feat['properties'])
                    writer.shape(feat['geometry'])

            print('packing into zipfile')
            # write shp
            with open(shapefile_path+'.shp', 'rb') as f:
                filename = 'osm_{}_{}.shp'.format(iso, osm_lvl)
                archive.writestr(filename, f.read())
            # write shx
            with open(shapefile_path+'.shx', 'rb') as f:
                filename = 'osm_{}_{}.shx'.format(iso, osm_lvl)
                archive.writestr(filename, f.read())
            # write dbf
            with open(shapefile_path+'.dbf', 'rb') as f:
                filename = 'osm_{}_{}.dbf'.format(iso, osm_lvl)
                archive.writestr(filename, f.read())

            print('calculating layer area')
            area = 0
            for feat in feats:
                geom = feat['geometry']
                if geom['type'] == 'Polygon':
                    exteriors = [geom['coordinates'][0]]
                elif geom['type'] == 'MultiPolygon':
                    exteriors = [poly[0] for poly in geom['coordinates']]
                for ring in exteriors:
                    area += abs(shapefile.signed_area(ring, fast=True))
            print('area:', area)

            # check if layer is complete
            # by ensuring the area remains roughly the same as level 0
            if adm_lvl == 0:
                area_0 = area
            else:
                if (area / area_0) < 0.95:
                    print('layer is incomplete (area is less than 95%% of level 0), skipping')
                    continue

            # add meta input args
            path = '{iso}.zip/osm_{iso}_{lvl}.shp'.format(iso=iso, lvl=osm_lvl)
            input_args = {'path':path,
                        'level':adm_lvl,
                        'type':None,
                        'name_field':'name'}
            inputs.append(input_args)
            print(input_args)

            adm_lvl += 1

    print('writing meta')
    meta = {"input":inputs,
            "year":None,
            "iso":iso,
            "source":["OSM-Boundaries","OpenStreetMap"],
            "source_updated":db_date,
            "source_url":"https://osm-boundaries.com/",
            "license":"OpenStreetMap License",
            "license_detail":"Creative Commons Attribution-ShareAlike 2.0",
            "license_url":"www.openstreetmap.org/copyright"
            }
    with open('{iso}/sourceMetaData.json'.format(iso=iso), 'w', encoding='utf8') as f:
        json.dump(meta, f, indent=True)


