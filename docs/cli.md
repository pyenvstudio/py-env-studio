# ⌨️ CLI Reference

## Create environment
```bash
py-env-studio --create <env_name>
```

## Create & upgrade pip
```bash
py-env-studio --create <env_name> --upgrade-pip
```

## Delete environment
```bash
py-env-studio --delete <env_name>
```

## List all environments
```bash
py-env-studio --list
```

## Install package
```bash
py-env-studio --install <env_name>,numpy
```

## Uninstall package
```bash
py-env-studio --uninstall <env_name>,numpy
```

## Export requirements
```bash
py-env-studio --export <env_name>,requirements.txt
```

## Import requirements
```bash
py-env-studio --import-reqs <env_name>,requirements.txt
```