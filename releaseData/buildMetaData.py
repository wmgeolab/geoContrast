
import os
import json
import csv
import urllib.request
import sys
sys.path.append('..')
import iotools
import re

#Initialize workspace
ws = {}
try:
    fdsfsfdsfsdf
    ws['working'] = os.environ['GITHUB_WORKSPACE']
    ws['logPath'] = os.path.expanduser("~") + "/tmp/log.txt"
except:
    ws['working'] = os.path.abspath("") # current folder ie releaseData
    ws['logPath'] = "buildMetaData-log.txt" #os.path.expanduser("~") + "/tmp/log.txt"
os.chdir(ws['working'])

#Load in the ISO lookup table
isoDetails = list(csv.DictReader(open("../buildData/iso_3166_1_alpha_3.csv", encoding="utf8")))

#Remove any old CSVs
gbContrastCSV = "geoContrast-meta.csv"
try:
    os.remove(gbContrastCSV)
except:
    pass

#Create output csv file with headers
fieldnames = "boundaryID,boundaryName,boundaryISO,boundaryYearRepresented,boundaryType,boundaryCanonical,nameField,boundarySource-1,boundarySource-2,boundaryLicense,licenseDetail,licenseSource,boundarySourceURL,sourceDataUpdateDate,buildUpdateDate,Continent,UNSDG-region,UNSDG-subregion,worldBankIncomeGroup,apiURL,boundaryCount,boundaryYearSourceLag,statsArea,statsPerimiter,statsVertices,statsLineResolution,statsVertexDensity".split(',')
wfob = open(gbContrastCSV, 'w', newline='', encoding='utf8')
writer = csv.DictWriter(wfob, fieldnames=fieldnames)
writer.writeheader()

#Loop all metadata json files in releaseData
for (path, dirname, filenames) in os.walk(ws["working"]):

    #Look for file metadata.json
    metaSearch = [x for x in filenames if x.endswith('metaData.json')]
    if(len(metaSearch)==1):
        print(metaSearch)

        #Init row from file metadata.json
        with open(path + "/" + metaSearch[0], "r", encoding='utf8') as j:
            meta = json.load(j)

        #Drop unwanted entries
        meta.pop('downloadURL')

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
        githubRoot = 'https://media.githubusercontent.com/media/wmgeolab/geoContrast/main' # lfs github files
        topoPath = path + "/" + metaSearch[0].replace('-metaData.json', '.topojson')
        topoPath = topoPath.replace('\\','/')
        relTopoPath = topoPath[topoPath.find('releaseData'):]
        meta['apiURL'] =  githubRoot + '/' + relTopoPath

        #Add in geometry statistics
        with open(path + "/" + metaSearch[0].replace('metaData.json','stats.json'), "r", encoding='utf8') as j:
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

#Add in csv entries based on the github geoBoundaries (Open) metadata file
rfob = urllib.request.urlopen('https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/geoBoundariesOpen-meta.csv')
reader = csv.DictReader(rfob.read().decode('utf-8').split('\n'))
for row in reader:
    # drop any additional 'blank' field values beyond fieldnames
    if '' in row.keys(): row.pop('')
    if None in row.keys(): row.pop(None)
    # set the nameField
    row['nameField'] = 'shapeName'
    # force the year field to int
    row['boundaryYearRepresented'] = int(float(row['boundaryYearRepresented']))
    # clear and set the source fields to 'geoBoundaries'
    # TODO: maybe the better way is to include an extra field that says the geoContrast source dataset
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
    resp = urllib.request.urlopen(apiURL.replace('.topojson', '.geojson'))
    try:
        geoj = json.loads(resp.read())
    except:
        # lfs github files
        apiURL = 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
        print('LFS', apiURL)
        row['apiURL'] = apiURL
        resp = urllib.request.urlopen(apiURL.replace('.topojson', '.geojson'))
        geoj = json.loads(resp.read())
    stats = iotools.calc_stats(geoj['features'], row)
    row.update(stats)
    # write ro row
    writer.writerow(row)

#Add in csv entries based on the github geoBoundaries (Humanitarian) metadata file
rfob = urllib.request.urlopen('https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/geoBoundariesHumanitarian-meta.csv')
reader = csv.DictReader(rfob.read().decode('utf-8').split('\n'))
for row in reader:
    # drop any additional 'blank' field values beyond fieldnames
    if '' in row.keys(): row.pop('')
    if None in row.keys(): row.pop(None)
    # set the nameField
    row['nameField'] = 'shapeName'
    # force the year field to int
    row['boundaryYearRepresented'] = int(float(row['boundaryYearRepresented']))
    # clear and set the source fields to 'geoBoundaries'
    # TODO: maybe the better way is to include an extra field that says the geoContrast source dataset
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
    resp = urllib.request.urlopen(apiURL.replace('.topojson', '.geojson'))
    try:
        geoj = json.loads(resp.read())
    except:
        # lfs github files
        apiURL = 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbHumanitarian/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
        print('LFS', apiURL)
        row['apiURL'] = apiURL
        resp = urllib.request.urlopen(apiURL.replace('.topojson', '.geojson'))
        geoj = json.loads(resp.read())
    stats = iotools.calc_stats(geoj['features'], row)
    row.update(stats)
    # write ro row
    writer.writerow(row)

#Add in csv entries based on the github geoBoundaries (Authoritative) metadata file
rfob = urllib.request.urlopen('https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/geoBoundariesAuthoritative-meta.csv')
reader = csv.DictReader(rfob.read().decode('utf-8').split('\n'))
for row in reader:
    # drop any additional 'blank' field values beyond fieldnames
    if '' in row.keys(): row.pop('')
    if None in row.keys(): row.pop(None)
    # set the nameField
    row['nameField'] = 'shapeName'
    # force the year field to int
    row['boundaryYearRepresented'] = int(float(row['boundaryYearRepresented']))
    # clear and set the source fields to 'geoBoundaries'
    # TODO: maybe the better way is to include an extra field that says the geoContrast source dataset
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
    resp = urllib.request.urlopen(apiURL.replace('.topojson', '.geojson'))
    try:
        geoj = json.loads(resp.read())
    except:
        # lfs github files
        apiURL = 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbAuthoritative/{iso}/{lvl}/geoBoundaries-{iso}-{lvl}.topojson'.format(iso=iso, lvl=lvl)
        print('LFS', apiURL)
        row['apiURL'] = apiURL
        resp = urllib.request.urlopen(apiURL.replace('.topojson', '.geojson'))
        geoj = json.loads(resp.read())
    stats = iotools.calc_stats(geoj['features'], row)
    row.update(stats)
    # write ro row
    writer.writerow(row)

#Close up shop
wfob.close()


