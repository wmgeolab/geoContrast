
import os
import json
import csv
import urllib.request
import sys
import re
from time import time

# init working dir
os.chdir(os.path.dirname(__file__))
sys.path.append('..')
import iotools

# params
if os.getenv('INPUT_GITHUB_ACTION', None):
    UPDATE_GB = os.environ['INPUT_UPDATE_GB']
else:
    UPDATE_GB = False

#Begin
start = time()

#Load in the ISO lookup table
isoDetails = list(csv.DictReader(open("../buildData/iso_3166_1_alpha_3.csv", encoding="utf8")))

#Remove any old CSVs
gbContrastCSV = "geoContrast-meta.csv"
try:
    os.remove(gbContrastCSV)
except:
    pass

#Create output csv file with headers
fieldnames = "boundaryCollection,boundaryName,boundaryISO,boundaryYearRepresented,boundaryType,boundaryCanonical,nameField,boundarySource-1,boundarySource-2,boundarySource-3,boundarySource-4,boundarySource-5,boundaryLicense,licenseDetail,licenseSource,boundarySourceURL,sourceDataUpdateDate,buildUpdateDate,Continent,UNSDG-region,UNSDG-subregion,worldBankIncomeGroup,apiURL,boundaryCount,boundaryYearSourceLag,statsArea,statsPerimeter,statsVertices,statsLineResolution,statsVertexDensity".split(',')
wfob = open(gbContrastCSV, 'w', newline='', encoding='utf8')
writer = csv.DictWriter(wfob, fieldnames=fieldnames)
writer.writeheader()

#Loop all metadata json files in releaseData
for (dirpath, dirname, filenames) in os.walk(os.path.abspath("")):

    #Look for file metadata.json
    metaSearch = [x for x in filenames if x.endswith('metaData.json')]
    for metaFile in metaSearch:
        print(metaFile)

        #Init row from file metadata.json
        with open(dirpath + "/" + metaFile, "r", encoding='utf8') as j:
            meta = json.load(j)

        #Remove keys not in metadata table
        meta.pop('note', None)

        #Add in boundary collection (ie the folder name that the boundary is organized into)
        reldirpath = dirpath.split('releaseData')[-1].strip('/').strip('\\')
        collection = reldirpath.split('/')[0].split('\\')[0] # topmost folder
        meta['boundaryCollection'] = collection

        #Handle some standard missing data...?
        if not meta['boundaryCanonical']:
            meta['boundaryCanonical'] = 'Unknown'

        #Fetch country info
        isoMeta = [row
                   for row in isoDetails
                   if row["Alpha-3code"] == meta['boundaryISO']]
        if len(isoMeta) == 0:
            continue
        else:
            isoMeta = isoMeta[0]

        #Add in country context
        for k in 'Country,Continent,UNSDG-region,UNSDG-subregion,worldBankIncomeGroup'.split(','):
            meta[k] = isoMeta[k]

        #Fix Country renamed to boundaryName
        meta['boundaryName'] = meta.pop('Country') 

        #Add in apiURL
        #githubRoot = 'https://raw.githubusercontent.com/wmgeolab/geoContrast/main' # normal github files
        githubRoot = 'https://media.githubusercontent.com/media/wmgeolab/geoContrast/stable' # lfs github files
        topoPath = dirpath + "/" + metaFile.replace('-metaData.json', '.topojson.zip')
        topoPath = topoPath.replace('\\','/')
        relTopoPath = topoPath[topoPath.find('releaseData'):]
        meta['apiURL'] =  githubRoot + '/' + relTopoPath

        #Add in geometry statistics
        with open(dirpath + "/" + metaFile.replace('metaData.json','stats.json'), "r", encoding='utf8') as j:
            stats = json.load(j)
            meta.update(stats)

        #Override erroneous boundaryYearSourceLag
        yr = meta['boundaryYearRepresented']
        updated = meta['sourceDataUpdateDate']
        updated_year_match = re.search('([0-9]{4})', updated)
        if yr == 'Unknown' or updated_year_match is None:
            meta['boundaryYearSourceLag'] = None
        else:
            meta['boundaryYearSourceLag'] = int(updated_year_match.group()) - yr
    
        # write row
        #print(meta)
        writer.writerow(meta)


##### Calc stats for geoBoundaries in separate csv

if UPDATE_GB:

    gbWfob = open('geoContrast-gbMeta.csv', 'w', newline='', encoding='utf8')
    gbWriter = csv.DictWriter(gbWfob, fieldnames=fieldnames)
    gbWriter.writeheader()

    #Add in csv entries based on the github geoBoundaries (Open) metadata file
    rfob = urllib.request.urlopen('https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/geoBoundariesOpen-meta.csv')
    reader = csv.DictReader(rfob.read().decode('utf-8').split('\n'))
    for row in reader:
        # drop any additional 'blank' field values beyond fieldnames
        if '' in row.keys(): row.pop('')
        if None in row.keys(): row.pop(None)
        row.pop('boundaryID')
        # set the nameField
        row['nameField'] = 'shapeName'
        # force the year field to int
        row['boundaryYearRepresented'] = int(float(row['boundaryYearRepresented']))
        # add in collection name
        row['boundaryCollection'] = 'geoBoundaries (Open)'
        # clear and set the source fields to 'geoBoundaries'
        # TODO: maybe the better way is to include an extra field that says the geoContrast source dataset
        row['boundarySource-3'] = row['boundarySource-2']
        row['boundarySource-2'] = row['boundarySource-1']
        row['boundarySource-1'] = 'geoBoundaries (Open)'
        # overwrite the gb apiURL with direct link to github
        iso = row['boundaryISO']
        lvl = row['boundaryType']
        apiURL = 'https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbOpen/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
        row['apiURL'] = apiURL
        print(apiURL)
        # fix gb url bugs
        row['licenseSource'] = row['licenseSource'].replace('https//','https://').replace('http//','http://')
        row['boundarySourceURL'] = row['boundarySourceURL'].replace('https//','https://').replace('http//','http://')
        # remove the old gb stats fields
        oldfields = ['meanPerimeterLengthKM', 'minAreaSqKM', 'maxVertices', 'maxAreaSqKM', 'meanVertices', 'maxPerimeterLengthKM', 'admUnitCount', 'meanAreaSqKM', 'minVertices', 'minPerimeterLengthKM']
        for field in oldfields:
            del row[field]
        # calculate geometry stats on-the-fly
        from topojson import geometry # this is the local topology.py file
        resp = urllib.request.urlopen(apiURL)
        try:
            topo = json.loads(resp.read())
        except:
            # lfs github files
            apiURL = 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
            print('LFS', apiURL)
            row['apiURL'] = apiURL
            resp = urllib.request.urlopen(apiURL)
            topo = json.loads(resp.read())
        lyr = list(topo['objects'].keys())[0]
        print('serializing')
        objects = topo['objects'][lyr]['geometries']
        arcs = topo['arcs']
        transform = topo['transform']
        features = []
        for obj in objects:
            try:
                geoj = geometry(obj, arcs, **transform)
                features.append({'type':'Feature', 'geometry':geoj})
            except Exception as err:
                print('ERROR! Excluding topojson object from spatial stats (could not convert to geojson):', err)
                continue
        print('calculating stats')
        stats = iotools.calc_stats(features)
        row.update(stats)
        # write ro row
        gbWriter.writerow(row)

    #Add in csv entries based on the github geoBoundaries (Humanitarian) metadata file
    rfob = urllib.request.urlopen('https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/geoBoundariesHumanitarian-meta.csv')
    reader = csv.DictReader(rfob.read().decode('utf-8').split('\n'))
    for row in reader:
        # drop any additional 'blank' field values beyond fieldnames
        if '' in row.keys(): row.pop('')
        if None in row.keys(): row.pop(None)
        row.pop('boundaryID')
        # set the nameField
        row['nameField'] = 'shapeName'
        # force the year field to int
        row['boundaryYearRepresented'] = int(float(row['boundaryYearRepresented']))
        # add in collection name
        row['boundaryCollection'] = 'geoBoundaries (Humanitarian)'
        # clear and set the source fields to 'geoBoundaries'
        # TODO: maybe the better way is to include an extra field that says the geoContrast source dataset
        row['boundarySource-3'] = row['boundarySource-2']
        row['boundarySource-2'] = row['boundarySource-1']
        row['boundarySource-1'] = 'geoBoundaries (Humanitarian)'
        # overwrite the gb apiURL with direct link to github
        iso = row['boundaryISO']
        lvl = row['boundaryType']
        apiURL = 'https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbHumanitarian/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
        row['apiURL'] = apiURL
        print(apiURL)
        # fix gb url bugs
        row['licenseSource'] = row['licenseSource'].replace('https//','https://').replace('http//','http://')
        row['boundarySourceURL'] = row['boundarySourceURL'].replace('https//','https://').replace('http//','http://')
        # remove the old gb stats fields
        oldfields = ['meanPerimeterLengthKM', 'minAreaSqKM', 'maxVertices', 'maxAreaSqKM', 'meanVertices', 'maxPerimeterLengthKM', 'admUnitCount', 'meanAreaSqKM', 'minVertices', 'minPerimeterLengthKM']
        for field in oldfields:
            del row[field]
        # calculate geometry stats on-the-fly
        from topojson import geometry # this is the local topology.py file
        resp = urllib.request.urlopen(apiURL)
        try:
            topo = json.loads(resp.read())
        except:
            # lfs github files
            apiURL = 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbHumanitarian/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
            print('LFS', apiURL)
            row['apiURL'] = apiURL
            resp = urllib.request.urlopen(apiURL)
            topo = json.loads(resp.read())
        lyr = list(topo['objects'].keys())[0]
        print('serializing')
        objects = topo['objects'][lyr]['geometries']
        arcs = topo['arcs']
        transform = topo['transform']
        features = []
        for obj in objects:
            try:
                geoj = geometry(obj, arcs, **transform)
                features.append({'type':'Feature', 'geometry':geoj})
            except Exception as err:
                print('ERROR! Excluding topojson object from spatial stats (could not convert to geojson):', err)
                continue
        print('calculating stats')
        stats = iotools.calc_stats(features)
        row.update(stats)
        # write ro row
        gbWriter.writerow(row)

    #Add in csv entries based on the github geoBoundaries (Authoritative) metadata file
    rfob = urllib.request.urlopen('https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/geoBoundariesAuthoritative-meta.csv')
    reader = csv.DictReader(rfob.read().decode('utf-8').split('\n'))
    for row in reader:
        # drop any additional 'blank' field values beyond fieldnames
        if '' in row.keys(): row.pop('')
        if None in row.keys(): row.pop(None)
        row.pop('boundaryID')
        # set the nameField
        row['nameField'] = 'shapeName'
        # force the year field to int
        row['boundaryYearRepresented'] = int(float(row['boundaryYearRepresented']))
        # add in collection name
        row['boundaryCollection'] = 'geoBoundaries (Authoritative)'
        # clear and set the source fields to 'geoBoundaries'
        # TODO: maybe the better way is to include an extra field that says the geoContrast source dataset
        row['boundarySource-3'] = row['boundarySource-2']
        row['boundarySource-2'] = row['boundarySource-1']
        row['boundarySource-1'] = 'geoBoundaries (Authoritative)'
        # overwrite the gb apiURL with direct link to github
        iso = row['boundaryISO']
        lvl = row['boundaryType']
        apiURL = 'https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/gbAuthoritative/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
        row['apiURL'] = apiURL
        print(apiURL)
        # fix gb url bugs
        row['licenseSource'] = row['licenseSource'].replace('https//','https://').replace('http//','http://')
        row['boundarySourceURL'] = row['boundarySourceURL'].replace('https//','https://').replace('http//','http://')
        # remove the old gb stats fields
        oldfields = ['meanPerimeterLengthKM', 'minAreaSqKM', 'maxVertices', 'maxAreaSqKM', 'meanVertices', 'maxPerimeterLengthKM', 'admUnitCount', 'meanAreaSqKM', 'minVertices', 'minPerimeterLengthKM']
        for field in oldfields:
            del row[field]
        # calculate geometry stats on-the-fly
        from topojson import geometry # this is the local topology.py file
        resp = urllib.request.urlopen(apiURL)
        try:
            topo = json.loads(resp.read())
        except:
            # lfs github files
            apiURL = 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbAuthoritative/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
            print('LFS', apiURL)
            row['apiURL'] = apiURL
            resp = urllib.request.urlopen(apiURL)
            topo = json.loads(resp.read())
        lyr = list(topo['objects'].keys())[0]
        print('serializing')
        objects = topo['objects'][lyr]['geometries']
        arcs = topo['arcs']
        transform = topo['transform']
        features = []
        for obj in objects:
            try:
                geoj = geometry(obj, arcs, **transform)
                features.append({'type':'Feature', 'geometry':geoj})
            except Exception as err:
                print('ERROR! Excluding topojson object from spatial stats (could not convert to geojson):', err)
                continue
        print('calculating stats')
        stats = iotools.calc_stats(features)
        row.update(stats)
        # write to row
        gbWriter.writerow(row)

    #Close up shop
    gbWfob.close()

##### Add in geoBoundaries from csv

with open('geoContrast-gbMeta.csv', newline='', encoding='utf8') as gbRfob:
    gbReader = csv.DictReader(gbRfob)
    for row in gbReader:
        
        #Override erroneous boundaryYearSourceLag
        #yr = row['boundaryYearRepresented']
        #updated = row['sourceDataUpdateDate']
        #updated_year_match = re.search('([0-9]{4})', updated)
        #if yr == 'Unknown' or updated_year_match is None:
        #    row['boundaryYearSourceLag'] = None
        #else:
        #    row['boundaryYearSourceLag'] = int(updated_year_match.group()) - yr
            
        writer.writerow(row)

#Close up shop
wfob.close()

print('finished! build took {} seconds'.format(time()-start))

