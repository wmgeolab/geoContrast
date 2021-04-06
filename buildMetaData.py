
import os
import re 
import json
import pandas as pd
#import geopandas

#Initialize workspace
ws = {}
try:
    fdsfsfdsfsdf
    ws['working'] = os.environ['GITHUB_WORKSPACE']
    ws['logPath'] = os.path.expanduser("~") + "/tmp/log.txt"
except:
    ws['working'] = os.path.abspath("") # top/current folder
    ws['logPath'] = "buildMetaData-log.txt" #os.path.expanduser("~") + "/tmp/log.txt"

#Load in the ISO lookup table
isoDetails = pd.read_csv(ws['working'] + "/dta/iso_3166_1_alpha_3.csv")


#Remove any old CSVs for each case
gbContrastCSV = ws["working"] + "/releaseData/geoContrast-meta.csv"

try:
    os.remove(gbContrastCSV)
except:
    pass

#Create headers for each CSV
def headerWriter(f):
    f.write("boundaryID,Country,boundaryISO,boundaryYear,boundaryType,boundaryCanonical,boundarySource-1,boundarySource-2,boundaryLicense,licenseDetail,licenseSource,boundarySourceURL,sourceDataUpdateDate,buildUpdateDate,Continent,UNSDG-region,UNSDG-subregion,worldBankIncomeGroup,apiURL,admUnitCount,meanVertices,minVertices,maxVertices,meanPerimeterLengthKM,minPerimeterLengthKM,maxPerimeterLengthKM,meanAreaSqKM,minAreaSqKM,maxAreaSqKM,\n")

with open(gbContrastCSV,'w+') as f:
    headerWriter(f)

for (path, dirname, filenames) in os.walk(ws["working"] + "/releaseData/"):
    csvPath = gbContrastCSV
    
    metaSearch = [x for x in filenames if re.search('metaData.json', x)]
    
    if(len(metaSearch)==1):
        print(metaSearch)
        with open(path + "/" + metaSearch[0], "r") as j:
            meta = json.load(j)

        #Temporary hacks (TODO: change at source instead)
        meta['boundaryID'] = '...'
        meta['boundaryYear'] = str(meta['boundaryYear'])
        meta['buildUpdateDate'] = '...'
        
        isoMeta = isoDetails[isoDetails["Alpha-3code"] == meta['boundaryISO']]
        if len(isoMeta) == 0:
            continue
        
        #Build the metadata
        metaLine = '"' + meta['boundaryID'] + '","' + isoMeta["Country"].values[0] + '","' + meta['boundaryISO'] + '","' + meta['boundaryYear'] + '","' + meta["boundaryType"] + '","'

        if("boundaryCanonical" in meta):
            if(len(meta["boundaryCanonical"])>0):
                metaLine = metaLine + meta["boundaryCanonical"] + '","'
            else:
                metaLine = metaLine + 'Unkown","'
        else:
            metaLine = metaLine + 'Unkown","'

        metaLine = metaLine + meta['boundarySource-1'] + '","' + meta['boundarySource-2'] + '","' + meta['boundaryLicense'] + '","' + meta['licenseDetail'] + '","' + meta['licenseSource'] + '","'
        metaLine = metaLine + meta['boundarySourceURL'] + '","' + meta['sourceDataUpdateDate'] + '","' + meta["buildUpdateDate"] + '","'
        
        
        metaLine = metaLine + isoMeta["Continent"].values[0] + '","' + isoMeta["UNSDG-region"].values[0] + '","'
        metaLine = metaLine + isoMeta["UNSDG-subregion"].values[0] + '","' 
        metaLine = metaLine + isoMeta["worldBankIncomeGroup"].values[0] + '","'

        metaLine = metaLine + '...' + '","'

        #Calculate geometry statistics
        #We'll use the geoJSON here, as the statistics (i.e., vertices) will be most comparable
        #to other cases.
##        geojsonSearch = [x for x in filenames if re.search('.geojson', x)]
##        with open(path + "/" + geojsonSearch[0], "r") as g:
##            geom = geopandas.read_file(g)
##        
##        admCount = len(geom)
##        
##        vertices=[]
##        for i, row in geom.iterrows():
##            n = 0
##            
##            if(row.geometry.type.startswith("Multi")):
##                for seg in row.geometry:
##                    n += len(seg.exterior.coords)
##            else:
##                n = len(row.geometry.exterior.coords)
##            
##            vertices.append(n) ###

        admCount = ''
        stat1 = '' #round(sum(vertices)/len(vertices),0)
        stat2 = '' #min(vertices)
        stat3 = '' #max(vertices)
        
        metaLine = metaLine + str(admCount) + '","' + str(stat1) + '","' + str(stat2) + '","' + str(stat3) + '","'

        #Perimeter Using WGS 84 / World Equidistant Cylindrical (EPSG 4087)
##        lengthGeom = geom.copy()
##        lengthGeom = lengthGeom.to_crs(epsg=4087)
##        lengthGeom["length"] = lengthGeom["geometry"].length / 1000 #km

        stat1 = '' #lengthGeom["length"].mean()
        stat2 = '' #lengthGeom["length"].min()
        stat3 = '' #lengthGeom["length"].max()
        metaLine = metaLine + str(stat1) + '","' + str(stat2) + '","' + str(stat3) + '","'

        #Area #mean min max Using WGS 84 / EASE-GRID 2 (EPSG 6933)
##        areaGeom = geom.copy()
##        areaGeom = areaGeom.to_crs(epsg=6933)
##        areaGeom["area"] = areaGeom['geometry'].area / 10**6 #sqkm

        stat1 = '' #areaGeom['area'].mean()
        stat2 = '' #areaGeom['area'].min()
        stat3 = '' #areaGeom['area'].max()
        
        metaLine = metaLine + str(stat1) + '","' + str(stat2) + '","' + str(stat3) + '","'
        #Cleanup
        metaLine = metaLine + '"\n'
        metaLine = metaLine.replace("nan","")

        print(metaLine)
        with open(csvPath,'a') as f:
            f.write(metaLine)
    

