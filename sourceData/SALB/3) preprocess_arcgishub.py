'''
This script converts the downloaded lpk to a zip file, finds the shapefile path,
and adds this as an 'input' entry to the partialMeta.txt file.
After this process, the files inside arcgisdownloads were manually
copied over to the appropriate ISO country folder. If the ISO already existed
from the official UN SALB website downloads, then only the source with the
latest year would be kept. 
'''

import os
import zipfile
import json

for fold,_,files in os.walk('arcgisdownloads'):
    print(fold,files)
    for fil in files:
        if fil.endswith(('.lpk','.zip')):
            # lpk is really just a zipfile, rename it as such
            if fil.endswith('.lpk'):
                oldfil = fil
                fil = fil.replace('.lpk','.zip')
                os.rename(os.path.join(fold, oldfil), os.path.join(fold, fil))
            # extract
            print('inspecting lpk/zipfile')
            shapefiles = []
            with zipfile.ZipFile(os.path.join(fold,fil), 'r') as archive:
                for name in archive.namelist():
                    if name.endswith('.shp'):
                        shapefiles.append(name)
            print('found', shapefiles)
            if not shapefiles:
                raise Exception('no shapefiles found')
            if len(shapefiles) > 1:
                raise Exception('>1 shapefiles')
            # update metadata file
            with open(os.path.join(fold,'partialMeta.txt'), encoding='utf8') as r:
                meta = json.loads(r.read())
            meta['input'] = fil + '/' + shapefiles[0]
            print(meta)
            with open(os.path.join(fold,'partialMeta.txt'), 'w', encoding='utf8') as w:
                w.write(json.dumps(meta, indent=4))
                      
            
