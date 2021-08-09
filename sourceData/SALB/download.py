'''
Downloads the latest available shapefiles/zipfiles for each country
and automatically generates the sourceMetaData.json file.

NOTE: the dates on the website and filenames are the start dates of temporal validity, not the end dates.
Metadata for year and source_updated has to be manually input by looking at the historical change table
on the country pages.
'''


import urllib.request
from zipfile import ZipFile
import os
import io
import sys
import json
import warnings
import datetime

# import iotools.py
# should be in the top repo folder
cur_dir = os.path.abspath('')
repo_dir = cur_dir.split('sourceData')[0]
sys.path.append(repo_dir)
import iotools

# access the gadm country download page
root = 'https://www.unsalb.org'

def parse_country_links(raw):
    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    elem = next(elems)

    # get all country links
    for elem in elems:
        if elem.startswith('a href="/data'):
            relUrl = elem.replace('a href=', '').strip('"')
            url = root + relUrl
            yield url

def iter_country_page_downloads(url):
    raw = urllib.request.urlopen(url).read().decode('utf8')

    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    elem = next(elems)

    # find all zipfile downloads (should contain shapefile)
    for elem in elems:
        if elem.startswith('span class="date-display'):
            date = next(elems)
            yr,mn,dy = date.split('/')
            yr,mn,dy = map(int, [yr,mn,dy])
            date = datetime.date(yr, mn, dy)
            print('DATE',date)
        if elem.startswith("a class='file'"):
            url = elem.replace("a class='file' href=", "").strip("'") # the url tag oddly uses single-quotes
            print('FILE',url)
            if url.endswith('.zip'):
                yield date, url

# loop pages and download+unzip each
print('downloading:')
page = 0 # starts at page 0
while True:
    url = '{}/data?page={}'.format(root, page)
    print('')
    print('looping country links from page', url)
    resp = urllib.request.urlopen(url)
    if resp.getcode() != 200:
        # reached the end/invalid page
        break

    # get country links
    raw = resp.read().decode('utf8')
    countrylinks = list(parse_country_links(raw))
    if len(countrylinks) == 0:
        # reached the end/invalid page
        break
    
    # loop
    for countrylink in countrylinks:
        print(countrylink)
        
        # get page downloads
        page_downloads = list(iter_country_page_downloads(countrylink))
        if len(page_downloads) == 0:
            print('No page downloads, skipping')
            continue
        if len(page_downloads) > 1:
            warnings.warn('More than one country page downloads: {}'.format(page_downloads))
        date,ziplink = page_downloads[0]
        
        # create country folder
        iso = countrylink[-3:].upper()
        if os.path.lexists(iso):
            # dont overwrite any existing folders
            # to protect any metadata that may have been manually edited
            print('Country folder already exists, skipping')
            continue
        else:
            os.mkdir(iso)
        
        # download zipfile
        zipname = ziplink.split('/')[-1]
        urllib.request.urlretrieve(ziplink, '{}/{}'.format(iso, zipname))
        
        # determine main entries for meta file
        archive = ZipFile(os.path.join(iso, zipname), 'r')
        shapefiles = [name
                     for name in archive.namelist()
                     if name.endswith('.shp')]
        if len(shapefiles) == 0:
            warnings.warn('Zipfile does not contain any shapefile: {}'.format(archive.namelist()))
            continue
        if len(shapefiles) > 1:
            warnings.warn('Zipfile contains more than one shapefile: {}'.format(shapefiles))
            # in most cases this appears to be two files 'BNDA_*' and 'BNDL_*'
            # it appears the one we want is 'BNDA_*'
            # sorting should fix it
            shapefile_name = sorted(shapefiles)[0]
        else:
            shapefile_name = shapefiles[0]
        shapefile_path = '{}/{}'.format(zipname, shapefile_name)

        # get info from shapefile
        reader = iotools.get_reader(os.path.join(iso, shapefile_path))
        fieldnames = [f[0] for f in reader.fields]
        if 'DATSOR' in fieldnames:
            for rec in reader.iterRecords():
                updated = rec['DATSOR']
                if updated and len(updated.split('/')) == 3:
                    break
            if updated:
                dy,mn,yr = updated.split('/')
                dy,mn,yr = map(int, [dy,mn,yr])
                updated = datetime.date(yr, mn, dy).isoformat()
                year = yr
        else:
            warnings.warn('source_update and year could not be determined, must be manually specified')
            updated = None
            year = None
        reader.close()

        # create metadata
        meta = {
            "input":shapefile_path,
            
            "iso":iso,
            "year":year,
            "level":2, # is salb always level 2? 
            "type_field":None,
            "name_field":"ADM2NM",
            
            "source":["UN SALB"],
            "source_updated":updated,
            "source_url":countrylink,
            "download_url":countrylink,
            "license":'UN SALB Data License',
            "license_detail":None,
            "license_url":"https://www.unsalb.org/sites/default/files/wysiwyg_uploads/docs_uploads/TermsOfUseSALB2021.pdf"
        }
        print(meta)

        # write metadata to file
        dst = os.path.join(iso, 'sourceMetaData.json')
        with open(dst, 'w', encoding='utf8') as fobj:
            json.dump(meta, fobj, indent=4)

    page += 1
        
