import shapefile
import pythongis as pg

types = ['region']
iso = 'AS'

def get_data(path, iso):
    d = pg.VectorData(fields=['adm_level'])
    reader = shapefile.Reader(path)
    max_level = 0
    for rec in reader.iterRecords(fields=['iso_countr','adm_level']):
        if rec['iso_countr'] == iso:
            shape = reader.shape(rec.oid)
            #rec = reader.record()
            d.add_feature([rec['adm_level']], shape.__geo_interface__)
            max_level = max(max_level, rec['adm_level'])
    print('max level', max_level)
    return d

def make_map(d):
    m = pg.renderer.Map(5000, 5000, background='white')
    m.add_layer(d, fillcolor={'key':'adm_level', 'breaks':'unique'}, 
                outlinewidth='0.5px')
    m.zoom_auto()
    m.zoom_out(1.1)
    m.add_legend(xy=('1%w','1%h'), anchor='nw')
    m.save(f'inspectdata-{iso}-{typ}.png')

for typ in types:
    path = f'whosonfirst-data-{typ}-latest.zip'
    d = get_data(path, iso)
    make_map(d)
