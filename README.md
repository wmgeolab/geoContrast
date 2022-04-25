# geoContrast
Data to support the comparison tool for geoBoundaries

# Changing or updating boundary sources

...

# Adding new boundary sources

New boundary sources are added by creating a new folder containing the raw source data
file, and a metadata file describing how to process that raw file. More... 

Note that all source shapefile/data files added to the repo must be LFS-tracked. 
This means that you cannot simply upload the file in the GitHub browser interface,
and because the repo is very large, doing it in GitHub Desktop will be very slow.
Instead, the recommended way to contribute data is using `git`, below are instructions for
how to do so:

1. setup repo
```
git init
git remote add origin https://github.com/wmgeolab/geoContrast
git remote -v
```

2. setup sparse checkout and lfs
For instance, if you're adding data to the "Other" boundary collection:
```
git sparse-checkout init --cone
git sparse-checkout set sourceData/Other
git lfs install
```

3. pull down latest version of the repo
```
git pull origin main --progress
```

4. do your local changes
e.g. add a new folder, a zipfile containing the boundary shapefile, and a sourceMetaData.json file. 

5. when finished, add all new/changed files and commit
```
git status --porcelain -unormal
git add -A
git commit -a -m "Commit message..."
```

6. local branch is auto named master, rename main to match the remote
```
git branch -m master main
```

7. push
```
git push origin main
```

# Deploying to the live website

By default, all data contributions to the `main` branch are considered work-in-progress and will not
affect the live website. Once the boundary data is ready and you wish to make it available to the 
comparison tool on the live website, simply create a PR from the `main` branch to the `stable` branch. 
Once accepted, users will be able access the latest boundaries from the website. 
