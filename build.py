
import iotools
import os
import json
import warnings
import traceback

# params
collections = ['OpenStreetMap']
isos = ['ALB','ARM']
replace = False
write_meta = True
write_stats = True
write_data = True

# begin
for dirpath,dirnames,filenames in os.walk('sourceData'):
    if 'sourceMetaData.json' in filenames:
        # load kwargs from meta file
        with open(os.path.join(dirpath, 'sourceMetaData.json'), encoding='utf8') as fobj:
            kwargs = json.loads(fobj.read())

        # determine the dataset name from the folder below sourceData
        reldirpath = os.path.relpath(dirpath, 'sourceData')
        collection = reldirpath.split('/')[0].split('\\')[0] # topmost folder

        # only process if collection is in the list of collections to be processed
        if collections and collection not in collections:
            continue

        # only process if iso is in the list isos to be processed
        # (only for iso-specific sources for now)
        if 'iso' in kwargs:
            # this is an iso-specific source
            if isos and kwargs['iso'] not in isos:
                continue
        
        print('')
        print('='*30)
        print('processing', dirpath)

        # define output dir
        output_dir = 'releaseData'

        # add final entries to kwargs
        kwargs.update(input_dir=dirpath,
                      collection=collection,
                      output_dir=output_dir,
                      write_meta=write_meta,
                      write_stats=write_stats,
                      write_data=write_data)

        # check if final output folder already exists
        # this the output_dir+dataset+ISO for country-specific sources ('iso'),
        # and the output_dir+dataset for global sources ('iso_field' or 'iso_path')
        # ...
        if 'iso' in kwargs:
            exists = os.path.lexists(os.path.join(output_dir, collection, kwargs['iso']))
        else:
            exists = os.path.lexists(os.path.join(output_dir, collection))

        # only process if output folder doesn't already exist or if replace == True
        if exists and replace == False:
            print('output folder already exists and replace = False, skipping')
            continue

        print('')
        print('reading sourceMetaData.json')

        # nest multiple inputs
        if 'input' not in kwargs:
            warnings.warn("metadata file for '{}' doesn't have correct format, skipping".format(dirpath))
            continue
        input_arg = kwargs.pop('input')
        if isinstance(input_arg, str):
            inputs = [{'path':input_arg}]
        elif isinstance(input_arg, list):
            inputs = input_arg
        else:
            raise Exception('input arg must be either string or list of dicts')
        # run one or more imports
        for input_kwargs in inputs:
            _kwargs = kwargs.copy()
            _kwargs.update(input_kwargs)
            _kwargs['input_path'] = _kwargs.pop('path') # rename path arg
            print('')
            print('-'*30)
            print('import args', _kwargs)
            try:
                iotools.import_data(**_kwargs)
            except Exception as err:
                warnings.warn("Error importing data for '{}': {}".format(dirpath, traceback.format_exc()))
