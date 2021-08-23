'''
Downloads the latest available shapefiles/zipfiles for each country
and automatically generates the sourceMetaData.json file.
'''


import urllib.request
from zipfile import ZipFile
import os
import io
import re
import sys
import json
import warnings
import datetime
import itertools

# import iotools.py
# should be in the top repo folder
cur_dir = os.path.abspath('')
repo_dir = cur_dir.split('sourceData')[0]
sys.path.append(repo_dir)
import iotools

# access the gadm country download page
root = 'https://international.ipums.org'

def iter_country_downloads(raw):
    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    elem = next(elems)

    # get all country links
    for elem in elems:
        #print(elem)
        if elem == 'tr':
            # first cell = country name
            next(elems) # first skip weird newline
            next(elems) # td
            country = next(elems)
            next(elems) # /td
            # second cell = type
            next(elems) # first skip weird newline
            next(elems) # td
            typ = next(elems)
            next(elems) # /td
        if elem.startswith('a href') and '.zip' in elem:
            # download links
            link = root + elem.replace('a href=', '').strip('"')
            filename = link.split('/')[-1]
            match = re.search(r'[0-9]{4}', filename)
            if match:
                year = int(match.group(0))
            else:
                raise Exception("Couldn't find year in {}".format(filename))
            iso = filename.split('_')[1][:2].upper() # 2 digit iso
            print('-->', country, iso, year, typ, link)
            assert all([iso, year, link])
            yield country, iso, year, typ, link
            #country = iso = year = link = None

# loop pages and download+unzip each
print('downloading:')
#start = 0 # starts at item 0
for level in [1,2,3]:
    subpage = {1: 'international/gis_yrspecific_1st.shtml',
               2: 'international/gis_yrspecific_2nd.shtml',
               3: 'international/gis_yrspecific_3rd.shtml'}[level]
    url = '{}/{}'.format(root, subpage)
    print('')
    print('looping country links from page', url)
    resp = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}))

    # get country links
    raw = resp.read().decode('utf8')
    countrylinks = list(iter_country_downloads(raw))

    # loop each country iso
    key = lambda x: x[1]
    countrylinks = itertools.groupby(sorted(countrylinks, key=key), key=key)
    for iso,group in countrylinks:
        group = list(group)

        # get only the entry for the latest year
        group = sorted(group, key=lambda x: x[2])
        country, iso, year, typ, link = group[-1]
        print('processing', country, iso, year, typ, link)
        
        # create download folder
        dst = os.path.join(iso, 'ADM{}'.format(level))
        if os.path.lexists(dst):
            print('ALREADY EXISTS, SKIPPING')
            continue
        os.makedirs(dst, exist_ok=True)
        
        # download file
        filename = link.split('/')[-1]
        urllib.request.urlretrieve(link, '{}/{}'.format(dst, filename))

        # get update date and shapefile input path
        updated = None
        archive = ZipFile('{}/{}'.format(dst, filename))
        for fil in archive.namelist():
            if fil.endswith('.xml'):
                raw = archive.open(fil).read().decode('utf8')
                try:
                    updated = raw.split('<ModDate>')[1][:8]
                    yr,mn,dy = updated[:4], updated[4:6], updated[6:8]
                    updated = '{}-{}-{}'.format(yr,mn,dy)
                except Exception as err:
                    warnings.warn("Couldn't find source update date for {}-{}: {}".format(iso, level, err))

        # get shapefile input path
        shapefiles = [fil for fil in archive.namelist() if fil.endswith('.shp')]
        if len(shapefiles) > 1:
            warnings.warn('Found {} shapefiles for {}-{}'.format(len(shapefiles), iso, level))
        shapefile_path = '{}/{}'.format(filename, shapefiles[0])

        # create metadata
        meta = {
            "input":shapefile_path,
            "iso":iso,
            "year":year,
            "level":level,
            "type":typ,
            
            "source":["IPUMS"],
            "source_url":url,
            "source_updated":updated,
            "license":'IPUMS Data License',
            "license_detail":None,
            "license_url":'https://international.ipums.org/international/citation.shtml',
        }
        print(meta)

        # write metadata to file
        path = os.path.join(dst, 'sourceMetaData.json')
        with open(path, 'w', encoding='utf8') as fobj:
            json.dump(meta, fobj, indent=4)

        
