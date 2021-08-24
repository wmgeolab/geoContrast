import py7zr
import zipfile
import os
import tempfile
import fiona

def sevenzip_to_zip(path):
    from_archive = py7zr.SevenZipFile(path, mode='r')
    name,ext = os.path.splitext(path)
    to_archive = zipfile.ZipFile(name + '.zip', 'w')
    filenames = list(from_archive.getnames())
    for fname in filenames:
        print(fname)
        fobj = from_archive.read(fname)[fname]
        raw = fobj.read()
        to_archive.writestr(fname, raw)
        from_archive.reset()

def gdb_to_shapefile(path, layer, target, droptypes=None):
    print(fiona.listlayers(path))
    basepath,ext = os.path.splitext(path)
    with fiona.open(path, layer=layer) as src:
        meta = src.meta
        print('src',meta)
        if droptypes:
            dropfields = [f for f,typ in meta['schema']['properties'].items() if typ in droptypes]
            for drop in dropfields:
                del meta['schema']['properties'][drop]
        meta['driver'] = 'ESRI Shapefile'
        print('dst',meta)
        with fiona.open(target, 'w', **meta) as dst:
            for f in src:
                if droptypes:
                    for drop in dropfields:
                        del f['properties'][drop]
                dst.write(f)

def mpk_to_shapefile(path, subpath, layer):
    # temporarily unzip the 7zip file
    archive = py7zr.SevenZipFile(path, mode='r')
    tempdir = tempfile.gettempdir()
    archive.extractall(tempdir)
    # convert unzipped gdb to shapefile
    from_path = os.path.join(tempdir, subpath)
    basepath,ext = os.path.splitext(path)
    to_path = basepath + '.shp'
    print(to_path)
    gdb_to_shapefile(from_path, layer, to_path)

# adm0
mpk_to_shapefile('World_Countries.mpk', 'v107/country.gdb', 'country')

# adm1
mpk_to_shapefile('World_Administrative_Divisions.mpk', 'v107/admin.gdb', 'admin')

