# extracts only the most recent layers
# also, adds iso codes since cshapes 2.0 doesn't contain iso codes

import shapefile
from zipfile import ZipFile, ZIP_DEFLATED
import io

# extract most recent layer
cshapes2 = shapefile.Reader('CShapes-2.0.zip/CShapes-2.0.shp', encoding='latin')
cshapes2_feats = [feat.__geo_interface__ for feat in cshapes2
                    if feat.record['gweyear']==2019]
print(len(cshapes2_feats))

# get gw-iso mapping from cshapes 1
cshapes1 = shapefile.Reader('cshapes_0.6.zip/cshapes.shp', encoding='latin')
cshapes1_feats = [feat.__geo_interface__ for feat in cshapes1
                    if feat.record['GWCODE']>=0 and feat.record['GWEYEAR']==2016]
gw2iso = {}
for feat in cshapes1_feats:
    gw = feat['properties']['GWCODE']
    iso = feat['properties']['ISO1AL3']
    if gw in gw2iso:
        raise Exception('More than one gwcode with same iso')
    gw2iso[gw] = iso

# add manual gw-iso entries not available in cshapes 1
gw2iso[6] = 'PRI' # puerto rico
gw2iso[65] = 'GLP' # guadeloupe
gw2iso[66] = 'MTQ' # martinique
gw2iso[120] = 'GUF' # french guyana
gw2iso[585] = 'REU' # reunion
gw2iso[930] = 'NCL' # New Caledonia and Dependencies
gw2iso[960] = 'PYF' # French Polynesia

# add iso entry to cshapes 2 feats
for feat in cshapes2_feats:
    gw = feat['properties']['gwcode']
    try:
        iso = gw2iso[gw]
        feat['properties']['iso3'] = iso
    except KeyError:
        print("Couldn't find gwcode: {}, {}".format(gw, feat['properties']['cntry_name']))

# write to file and zip
with ZipFile('CShapes-2.0-extracted.zip', mode='w', compression=ZIP_DEFLATED) as archive:
    # write shapefile to memory
    shp = io.BytesIO()
    shx = io.BytesIO()
    dbf = io.BytesIO()
    with shapefile.Writer(shp=shp, shx=shx, dbf=dbf) as w:
        w.fields = list(cshapes2.fields)
        w.field('iso3', 'C', 3)
        print(w.fields)
        for feat in cshapes2_feats:
            w.record(**feat['properties'])
            w.shape(feat['geometry'])
    # write into zipfile
    archive.writestr('CShapes-2.0.shp', shp.getvalue())
    archive.writestr('CShapes-2.0.shx', shx.getvalue())
    archive.writestr('CShapes-2.0.dbf', dbf.getvalue())
