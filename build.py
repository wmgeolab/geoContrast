
import iotools
import os
import json
import warnings

# params
sources = ['GRID3','OCHA','Natural_Earth','GADM']
write_meta = False
write_stats = True
write_data = False

# begin
for dirpath,dirnames,filenames in os.walk('sourceData'):
    if 'sourceMetaData.json' in filenames:
        # load kwargs from meta file
        with open(os.path.join(dirpath, 'sourceMetaData.json'), encoding='utf8') as fobj:
            kwargs = json.loads(fobj.read())

        # determine the dataset name from the folder below sourceData
        reldirpath = os.path.relpath(dirpath, 'sourceData')
        data_name = reldirpath.split('/')[0].split('\\')[0] # topmost folder

        # only process if data_name is in the list of sources to be processed
        if sources and data_name not in sources:
            continue
        print('processing', dirpath)

        # define output dir
        output_dir = 'releaseData'

        # add final entries to kwargs
        kwargs.update(input_dir=dirpath,
                      data_name=data_name,
                      output_dir=output_dir,
                      write_meta=write_meta,
                      write_stats=write_stats,
                      write_data=write_data)

        # decide whether to import or not
        # this should be determined based on whether the output_dir+dataset+ISO
        # exists for country-specific sources ('iso'),
        # and whether the output_dir+dataset exists for global sources ('iso_field'
        # or 'iso_path')
        # ...
        if 'iso' in kwargs:
            exists = os.path.lexists(os.path.join(output_dir, data_name, kwargs['iso']))
        else:
            exists = os.path.lexists(os.path.join(output_dir, data_name))

        if (not exists) or write_meta is True or write_stats is True:
            print('')
            print('='*30)
            print('reading sourceMetaData.json')
            # nest multiple inputs
            if 'input' not in kwargs:
                warnings.warn("metadata file doesn't have correct format, skipping")
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
                iotools.import_data(**_kwargs)
