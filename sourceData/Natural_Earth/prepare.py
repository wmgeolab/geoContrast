import shapefile
from zipfile import ZipFile, ZIP_DEFLATED
import io

# the iso_a2/3 fields are the only valid iso codes
# the other similar fields are custom natural earth codes
# but need to fill in some missing iso_a2/3 codes
# https://github.com/nvkelso/natural-earth-vector/issues/112

with ZipFile('ne_10m_admin_x_prepped.zip', mode='w', compression=ZIP_DEFLATED) as archive:

    # adm0
    with shapefile.Writer(shp=io.BytesIO(), shx=io.BytesIO(), dbf=io.BytesIO()) as w:
        r = shapefile.Reader('sourceData/Natural_Earth/ne_10m_admin_0_countries.zip')
        w.fields = list(r.fields)
        for shaperec in r.iterShapeRecords():
            dct = shaperec.record.as_dict()
            if dct['NAME']=='Norway':
                dct.update(ISO_A2='NO', ISO_A3='NOR')
            if dct['NAME']=='France':
                dct.update(ISO_A2='FR', ISO_A3='FRA')
            if dct['NAME']=='Kosovo':
                dct.update(ISO_A2='XK', ISO_A3='XKX')
            w.record(**dct)
            w.shape(shaperec.shape)

    for ext in 'shp shx dbf'.split():
        data = getattr(w, ext).getvalue()
        archive.writestr(f'ne_10m_admin_0_countries.{ext}', data)

    # adm1
    with shapefile.Writer(shp=io.BytesIO(), shx=io.BytesIO(), dbf=io.BytesIO()) as w:
        r = shapefile.Reader('sourceData/Natural_Earth/ne_10m_admin_1_states_provinces.zip')
        w.fields = list(r.fields)
        for shaperec in r.iterShapeRecords():
            dct = shaperec.record.as_dict()
            if dct['geonunit']=='Norway':
                dct.update(iso_a2='NO')
            if dct['geonunit']=='France':
                dct.update(iso_a2='FR')
            if dct['geonunit']=='Kosovo':
                dct.update(iso_a2='XK')
            w.record(**dct)
            w.shape(shaperec.shape)
    
    for ext in 'shp shx dbf'.split():
        data = getattr(w, ext).getvalue()
        archive.writestr(f'ne_10m_admin_1_states_provinces.{ext}', data)

    # adm2
    with shapefile.Writer(shp=io.BytesIO(), shx=io.BytesIO(), dbf=io.BytesIO()) as w:
        r = shapefile.Reader('sourceData/Natural_Earth/ne_10m_admin_2_counties.zip')
        w.fields = list(r.fields)
        for shaperec in r.iterShapeRecords():
            dct = shaperec.record.as_dict()
            if dct['GEONUNIT']=='Norway':
                dct.update(ISO_A2='NO')
            if dct['GEONUNIT']=='France':
                dct.update(ISO_A2='FR')
            if dct['GEONUNIT']=='Kosovo':
                dct.update(ISO_A2='XK')
            w.record(**dct)
            w.shape(shaperec.shape)
    
    for ext in 'shp shx dbf'.split():
        data = getattr(w, ext).getvalue()
        archive.writestr(f'ne_10m_admin_2_counties.{ext}', data)

