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
root = 'https://www.arcgis.com/home/group.html?id=3178d6e4fe384cda99fbaab5ee8c1fd7&view=list&searchTerm=&num=20#content'

def iter_country_downloads(raw):
    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    elem = next(elems)

    # get all country links
    for elem in elems:
        #print(elem)
        if elem.startswith('a class="card-title-link'):
            source_url = elem.split('href=')[1].strip('"')
            source_url = 'https://www.arcgis.com/home/' + source_url
            title = next(elems)
            year = title[-5:-1]
            #print(999,title,year)
        if 'Updated:' in elem:
            updated = elem.replace('Updated:','').strip()
            #print(999,updated)
        if elem.startswith('a role="menuitem"'):
            nxt = next(elems)
            if nxt == 'Download':
                download_url = elem.split('href=')[1].split('class=')[0].strip().strip('"')
                #print(999,download_url)
                print('-->', title, year, updated, source_url, download_url)
                assert all([title, year, updated, source_url, download_url])
                yield title, year, updated, source_url, download_url
                title = year = updated = source_url = download_url = None

# loop pages and download+unzip each
print('downloading:')
#start = 0 # starts at item 0
for listfile in ['arcgisdownloads/listpage1.txt', 'arcgisdownloads/listpage2.txt']:
    #url = '{}&start={}'.format(root, start)
    print('')
    print('looping country links from file', listfile)
    #resp = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}))
    #if resp.getcode() != 200:
    #    # reached the end/invalid page
    #    break

    # get country links
    with open(listfile, encoding='utf8') as r:
        raw = r.read()
    countrylinks = list(iter_country_downloads(raw))
    if len(countrylinks) == 0:
        # reached the end/invalid page
        break
    
    # loop
    for title, year, updated, source_url, download_url in countrylinks:
        print(title, download_url)
        
        # create download folder
        if os.path.lexists('arcgisdownloads/'+title):
            print('ALREADY EXISTS, SKIPPING')
            continue
        os.mkdir('arcgisdownloads/'+title)
        
        # download lpk file
        urllib.request.urlretrieve(download_url, '{}/{}/{}'.format('arcgisdownloads', title, 'download.lpk'))

        # create metadata
        meta = {
            "source_url":source_url,
            
            "year":year,
            
            "source":["UN SALB"],
            "source_updated":updated,
            "source_url":source_url,
            "download_url":source_url,
            "license":'Creative Commons Attribution-Noncommercial-No Derivative Works 3.0 Unported License',
            "license_detail":None,
            "license_url":source_url,
        }
        print(meta)

        # write metadata to file
        dst = os.path.join('arcgisdownloads', title, 'partialMeta.txt')
        with open(dst, 'w', encoding='utf8') as fobj:
            json.dump(meta, fobj, indent=4)

    #start += len(countrylinks) + 1
        
