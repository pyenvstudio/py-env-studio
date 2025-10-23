# ⌨️ CLI Reference

## Create environment
    py-env-studio --create <<env_name>>

## Create & upgrade pip
    py-env-studio --create <<env_name>> --upgrade-pip

## Delete environment
    py-env-studio --delete <<env_name>>

## List all environments
    py-env-studio --list

## Install package
    py-env-studio --install <<env_name>>,numpy

## Uninstall package
    py-env-studio --uninstall <<env_name>>,numpy

## Export requirements
    py-env-studio --export <<env_name>>,requirements.txt

## Import requirements
    py-env-studio --import-reqs <<env_name>>,requirements.txt

## Activating Environments
Manually activate your environment after creation:

Windows:

    .\envs\<environment name>\Scripts\activate

Linux/macOS:

    source envs/<environment name>/bin/activate
