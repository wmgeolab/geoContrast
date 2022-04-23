
import urllib.request
from zipfile import ZipFile
import io

# access the gadm country download page
root = 'https://gadm.org/download_country.html'
raw = urllib.request.urlopen(root).read().decode('utf8')

# hacky parse the html into elements
elems = raw.replace('>','<').split('<')
elems = (elem for elem in elems)
elem = next(elems)

# get all isos from the download page
print('list of isos:')
isos = []
while elem != None:
    if elem.startswith('option value="'):
        elem = elem.replace('option value="', '')
        iso = elem[:3]
        if len(iso)==3 and iso.isalpha():
            print(iso)
            isos.append(iso)
    elem = next(elems, None)

# loop isos and download+unzip each
print('downloading:')
for iso in isos:
    print(iso)
    url = 'https://geodata.ucdavis.edu/gadm/gadm4.0/shp/gadm40_{}_shp.zip'.format(iso)
    dst = 'countryfiles/{}.zip'.format(iso)
    urllib.request.urlretrieve(url, dst)
