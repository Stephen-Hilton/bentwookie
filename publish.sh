setop
echo "Remeber to update the version in the pyproject.toml file."
echo "You can do it now, if needed.  Press enter when ready."
read _ 

cd ~/Dev/bentwookie
rm -r dist src/*.egg-info

# activate the virtualenv
if [[ "$VIRTUAL_ENV" != *"venv_bentwookie"* ]]; then
    source ~/.venv_bentwookie/bin/activate
fi

# install build tools and make sure requirements are met
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install --upgrade twine
python3 -m pip install --upgrade build
python3 -m pip install --upgrade setuptools
python3 -m build

# check before we upload:
twine check dist/*

# upload
twine upload -r pypi dist/*
# twine upload -r testpypi dist/*