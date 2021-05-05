
import os
import json
import csv

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
isoDetails = list(csv.DictReader(open("../buildData/iso_3166_1_alpha_3.csv")))

#Remove any old CSVs
gbContrastCSV = "geoContrast-meta.csv"
try:
    os.remove(gbContrastCSV)
except:
    pass

#Create output csv file with headers
fieldnames = "boundaryID,Country,boundaryISO,boundaryYear,boundaryType,boundaryCanonical,boundarySource-1,boundarySource-2,boundaryLicense,licenseDetail,licenseSource,boundarySourceURL,sourceDataUpdateDate,buildUpdateDate,Continent,UNSDG-region,UNSDG-subregion,worldBankIncomeGroup,apiURL,admUnitCount,meanVertices,minVertices,maxVertices,meanPerimeterLengthKM,minPerimeterLengthKM,maxPerimeterLengthKM,meanAreaSqKM,minAreaSqKM,maxAreaSqKM".split(',')
fobj = open(gbContrastCSV, 'w', newline='')
writer = csv.DictWriter(fobj, fieldnames=fieldnames)
writer.writeheader()

#Loop all metadata json files in releaseData
for (path, dirname, filenames) in os.walk(ws["working"]):

    #Look for file metadata.json
    metaSearch = [x for x in filenames if x.endswith('metaData.json')]
    if(len(metaSearch)==1):
        print(metaSearch)

        #Init row from file metadata.json
        with open(path + "/" + metaSearch[0], "r") as j:
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

        #Add in apiURL
        #githubRoot = 'https://raw.githubusercontent.com/wmgeolab/geoContrast/main' # normal github files
        githubRoot = 'https://media.githubusercontent.com/media/wmgeolab/geoContrast/main' # lfs github files
        topoPath = path + "/" + metaSearch[0].replace('-metaData.json', '.topojson')
        topoPath = topoPath.replace('\\','/')
        relTopoPath = topoPath[topoPath.find('releaseData'):]
        meta['apiURL'] =  githubRoot + '/' + relTopoPath

        #Calculate geometry statistics
##        #We'll use the geoJSON here, as the statistics (i.e., vertices) will be most comparable
##        #to other cases.
####        geojsonSearch = [x for x in filenames if re.search('.geojson', x)]
####        with open(path + "/" + geojsonSearch[0], "r") as g:
####            geom = geopandas.read_file(g)
####        
####        admCount = len(geom)
####        
####        vertices=[]
####        for i, row in geom.iterrows():
####            n = 0
####            
####            if(row.geometry.type.startswith("Multi")):
####                for seg in row.geometry:
####                    n += len(seg.exterior.coords)
####            else:
####                n = len(row.geometry.exterior.coords)
####            
####            vertices.append(n) ###
##
##        admCount = ''
##        stat1 = '' #round(sum(vertices)/len(vertices),0)
##        stat2 = '' #min(vertices)
##        stat3 = '' #max(vertices)
##        
##        metaLine = metaLine + str(admCount) + '","' + str(stat1) + '","' + str(stat2) + '","' + str(stat3) + '","'
##
##        #Perimeter Using WGS 84 / World Equidistant Cylindrical (EPSG 4087)
####        lengthGeom = geom.copy()
####        lengthGeom = lengthGeom.to_crs(epsg=4087)
####        lengthGeom["length"] = lengthGeom["geometry"].length / 1000 #km
##
##        stat1 = '' #lengthGeom["length"].mean()
##        stat2 = '' #lengthGeom["length"].min()
##        stat3 = '' #lengthGeom["length"].max()
##        metaLine = metaLine + str(stat1) + '","' + str(stat2) + '","' + str(stat3) + '","'
##
##        #Area #mean min max Using WGS 84 / EASE-GRID 2 (EPSG 6933)
####        areaGeom = geom.copy()
####        areaGeom = areaGeom.to_crs(epsg=6933)
####        areaGeom["area"] = areaGeom['geometry'].area / 10**6 #sqkm
##
##        stat1 = '' #areaGeom['area'].mean()
##        stat2 = '' #areaGeom['area'].min()
##        stat3 = '' #areaGeom['area'].max()
##        
##        metaLine = metaLine + str(stat1) + '","' + str(stat2) + '","' + str(stat3) + '","'

        # write row
        #print(meta)
        writer.writerow(meta)

fobj.close()
    

