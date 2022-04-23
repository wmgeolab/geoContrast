
import iotools
import os
import json
import logging
import traceback
import sys
from datetime import datetime

# params
if os.getenv('INPUT_IS_GITHUB_ACTION', None):
    # args from github actions
    collections = os.environ['INPUT_COLLECTIONS'].split(',') if os.environ['INPUT_COLLECTIONS'] else []
    isos = os.environ['INPUT_ISOS'].split(',') if os.environ['INPUT_ISOS'] else []
    replace = os.environ['INPUT_REPLACE'].lower() in ('true', '1', 't')
    write_meta = os.environ['INPUT_WRITE_META'].lower() in ('true', '1', 't')
    write_stats = os.environ['INPUT_WRITE_STATS'].lower() in ('true', '1', 't')
    write_data = os.environ['INPUT_WRITE_DATA'].lower() in ('true', '1', 't')

    # no need for logfile, github action keeps its own log
    logger = None
else:
    # locally specified args
    collections = ['Natural_Earth']
    isos = [] #['NOR','CHL','CAN','FRA','USA']
    replace = False
    write_meta = True
    write_stats = True
    write_data = True

    # redirect to logfile
    logger = open('build_log.txt', mode='w', encoding='utf8', buffering=1)
    sys.stdout = logger
    sys.stderr = logger

# begin
error_count = 0
print('start time', datetime.now())
print('input args', [collections,isos,replace,write_meta,write_stats,write_data])
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
            error_count += 1
            logging.warning("metadata file for '{}' doesn't have correct format, skipping".format(dirpath))
            continue
        input_arg = kwargs.pop('input')
        if isinstance(input_arg, str):
            inputs = [{'path':input_arg}]
        elif isinstance(input_arg, list):
            inputs = input_arg
        else:
            error_count += 1
            logging.warning("metadata file for '{}' contains an error, skipping (input arg must be either string or list of dicts)".format(dirpath))
            continue
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
                error_count += 1
                logging.warning("error importing data for '{}': {}".format(_kwargs['input_path'], traceback.format_exc()))
                
print('end time', datetime.now())

if error_count > 0:
    print('build script encountered a total of {} errors'.format(error_count))
    raise Exception('Build script encountered a total of {} errors'.format(error_count))

if logger:
    logger.close()
