import bz2
import tarfile
import shutil
import json
import os
import sys
import shapefile
from zipfile import ZipFile, ZIP_DEFLATED

logger = open('prepare_log.txt', 'w', encoding='utf8')
sys.stdout = logger
sys.stderr = logger

iso_lookup = {}

def wof_to_shapefile(typ):
    basepath = f'whosonfirst-data-{typ}-latest'
    path = basepath + '.tar.bz2'
    temp_path = basepath + '.tar'

    if not os.path.lexists(temp_path):
        print('unpacking')
        with bz2.open(path) as src, open(temp_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)

    alt_count = 0
    nonpoly_count = 0

    with tarfile.TarFile(temp_path) as src_archive, shapefile.Writer(basepath+'.shp') as w:
        w.field('iso_country', 'C', 3)
        w.field('adm_level', 'N', 1)
        w.field('wof_id', 'N', 15)  
        w.field('wof_name', 'C', 150)
        w.field('wof_placetype', 'C', 50)
        w.field('wof_hierarchy', 'C', 254)
        w.field('wof_lastmodified', 'N', 15)
        w.field('wof_repo', 'C', 30)
        w.field('wof_superceded_by', 'C', 20)
        w.field('src_geom', 'C', 50)
        w.field('geom_bbox', 'C', 50)
        w.field('edtf_inception', 'C', 15)
        w.field('edtf_cessation', 'C', 15)
        for i,name in enumerate(src_archive.getnames()):
            if name.endswith('.geojson'):
                if '-alt-' in name:
                    alt_count += 1
                    #print('skipping alternative geom')
                    continue

                fobj = src_archive.extractfile(name)
                geoj = json.loads(fobj.read())
                #print(json.dumps(geoj['properties'], indent=4))

                if not 'Polygon' in geoj['geometry']['type']:
                    #print('not a polygon! instead {}'.format(geoj['geometry']['type']))
                    nonpoly_count += 1
                    continue

                if not geoj['properties']['iso:country']:
                    continue
                
                # skip problematic levels
                if geoj['properties']['iso:country']=='AU':
                    # non-contiguous city areas
                    if 'macrocounty' in basepath or 'county' in basepath or 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='GB':
                    # almost identical to region
                    if '-county-' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='ZA':
                    # partial?
                    if 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='XK':
                    # bad overlapping geoms
                    if '-region-' in basepath or 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='US':
                    # only northeast
                    if 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='SI':
                    # bad overlapping geoms
                    if '-region-' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='RU':
                    # partial?
                    if 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='RS':
                    # identical to higher level
                    if 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='NZ':
                    # partial
                    if 'localadmin' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='LI':
                    # identical to higher level
                    if '-region-' in basepath:
                        print('custom skipped')
                        continue
                if geoj['properties']['iso:country']=='BR':
                    # partial
                    if 'localadmin' in basepath:
                        print('custom skipped')
                        continue

                # begin
                print(i,name)

                # determine level
                # hier = geoj['properties']['wof:hierarchy']
                # if len(hier) > 0:
                #     leveltypes = [typ for typ in hier[0] # can be multiple hierarchies, assume the first one is correct
                #                 if typ[:-3] in 'country macroregion region macrocounty county localadmin'.split()]
                #     level = len(leveltypes) - 1 # hierarhcy includes self
                #     if len(hier) > 1:
                #         print('warning, more than one hierarchy! only first one used')
                # else:
                #     print('warning, unable to determine admin level, hierarchy missing!')
                #     continue

                # somehow, need to determine level as the max or most common level for country of that type
                # ... 

                # determine level based on previously detected types
                iso = geoj['properties']['iso:country']
                iso_types = iso_lookup.get(iso, None)
                if iso_types:
                    # add type to existing country entry
                    if not typ in iso_types:
                        iso_types.add(typ)
                        print(iso, len(iso_types)-1)
                else:
                    # first country entry
                    iso_types = set([typ])
                    iso_lookup[iso] = iso_types
                    print(iso, len(iso_types)-1)
                level = len(iso_types) - 1  # level based on number previous added types

                # get props
                props = {'adm_level': level}
                for k,v in geoj['properties'].items():
                    if k.startswith('edtf:') or k in ('geom:bbox','iso:country','src:geom','wof:hierarchy','wof:id','wof:placetype','wof:lastmodified','wof:name','wof:repo','wof:superceded_by'):
                        if isinstance(v, (dict,list)):
                            v = json.dumps(v) if v else None
                        if k.startswith('edtf') and v == 'uuuu':
                            v = None
                        props[k.replace(':','_')] = v

                #print(props)
                w.record(**props)
                w.shape(geoj['geometry'])

    print('{} of {} geoms written to shapefile'.format(len(w), i+1))
    print('{} alternate geoms, and {} non-polygon geoms were skipped'.format(alt_count, nonpoly_count))

    print('zipping')

    with ZipFile(basepath + '.zip', mode='w', compression=ZIP_DEFLATED) as dst_archive:
        for ext in 'shp shx dbf'.split():
            writefrom = open(basepath + '.' + ext, 'rb')
            dst_archive.writestr(basepath + '.' + ext, writefrom.read())
            #writeto = dst_archive.open(basepath + '.' + ext, mode='w')
            #shutil.copyfileobj(writefrom, writeto)
            writefrom.close()
            #writeto.close()
            os.remove(basepath + '.' + ext)

    os.remove(temp_path)

for typ in 'country dependency macroregion region macrocounty county localadmin'.split():
    print('')
    print(typ)
    wof_to_shapefile(typ)
