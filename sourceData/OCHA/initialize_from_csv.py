'''
Downloads zipfiles containing shapefiles for each country
and automatically generates the sourceMetaData.json file.

Does so using precollected csv file containing most of the necessary
metadata. Output should be checked.

Countries for which shapefiles couldnt be automatically found:
MMR (link was for search results of relevant datasets)
    [but excluding anyway since "MIMU geospatial datasets cannot be used on online platform unless with prior written agreement from MIMU"]
GNB (zipfile was empty, had to instead download the gdb and convert to zipped shapefile)
ARE (file was a .rar file, so had to be manually downloaded+unzipped)
TJK (source_url was missing, but turns out spatial datasets exists on all of HDX)

Countries in the csv that were not related to OCHA and hence moved to the "Other" collection
'''


import urllib.request
from zipfile import ZipFile
import os
import io
import sys
import json
import warnings
import datetime
import csv
from openpyxl import load_workbook

# read csv
wb = load_workbook(filename='meta.xlsx')
table = wb.worksheets[0]
exceldata = list(table.values)
fields = list(exceldata[0])
rows = []
for _row in exceldata[1:]:
    row = dict(zip(fields, _row))
    rows.append(row)

#with open('meta.xlsx', newline='', encoding='utf8') as f:
#    rows = list(csv.DictReader(f))

# loop rows of csv
for row in rows:
    # skip if the iso folder already exists
    iso = row['iso3']
    print('')
    print(iso)
    if os.path.lexists(iso):
        warnings.warn('iso {} already exists, skipping'.format(iso))
        continue
    else:
        os.mkdir(iso)

    # get sources
    source_url = row['src_url']
    if not source_url:
        warnings.warn('iso {} has no source_url, skipping'.format(iso))
        continue
    sources = []
    if row['src_org']:
        sources.append(row['src_org'])
    if row['src_name']:
        sources.append(row['src_name'])

    # dates
    year = row['src_date'].year if row['src_date'] else None
    updated = row['src_update'].strftime('%Y-%m-%d') if row['src_update'] else None
    if not updated:
        warnings.warn('Missing update date for {}'.format(iso))
    if not year:
        warnings.warn('Missing year for {}'.format(iso))

    # license
    license = 'Creative Commons Attribution for Intergovernmental Organisations'
    license_url = source_url

    # download zipfiles containing shapefiles
    try:
        resp = urllib.request.urlopen(source_url)
    except urllib.error.HTTPError:
        warnings.warn('Bad source url for {}: {}'.format(iso, source_url))
        continue
    raw = resp.read().decode('utf8')
    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    # determine input paths from zipfile/shapefile links
    inputs = []
    root = 'https://data.humdata.org'
    for elem in elems:
        if elem.startswith('a href') and '.zip' in elem:
            start = elem.find('"') + 1
            end = elem.find('"', start)
            link = root + elem[start:end]
            zipname = link.split('/')[-1]
            if '_admall_' in zipname.lower():
                continue
            print('fetching:', link)
            try:
                resp = urllib.request.urlopen(link)
            except urllib.error.HTTPError:
                warnings.warn('Bad link for: {}'.format(link))
                continue
            rawzip = resp.read()
            f = io.BytesIO(rawzip)
            archive = ZipFile(f)
            shapefiles = [fil for fil in archive.namelist() if fil.endswith('.shp')]
            if shapefiles:
                print('found zipfile with shapefiles', zipname, shapefiles)
                # output the zipfile
                with open('{}/{}'.format(iso, zipname), 'wb') as w:
                    w.write(rawzip)
                # add to input
                for subfile in shapefiles:
                    if '_admall_' in subfile.lower():
                        continue
                    path = '{}/{}'.format(zipname, subfile)
                    entry = {'path':path,
                             'level':None,
                             'type':None,
                             'name_field':None,
                             }
                    inputs.append(entry)
    if not inputs:
        warnings.warn("Couldn't find any zipfiles with shapefiles for {}".format(iso))

    # create meta
    meta = {'input':inputs,
            'iso':iso,
            'year':year,
            
            'source':sources,
            'source_updated':updated,
            'source_url':source_url,

            'license':license,
            'license_url':license_url,
            }
    print(meta)

    # write meta
    with open(iso+'/sourceMetaData.json', 'w', encoding='utf8') as f:
        f.write(json.dumps(meta, indent=4))
    

        
