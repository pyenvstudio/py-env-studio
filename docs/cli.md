# ⌨️ CLI Reference

```bash
# Create environment
py-env-studio --create <env_name>

# Create & upgrade pip
py-env-studio --create <env_name> --upgrade-pip

# Delete environment
py-env-studio --delete <env_name>

# List all environments
py-env-studio --list

# Install / uninstall package
py-env-studio --install <env_name>,numpy
py-env-studio --uninstall <env_name>,numpy

# Export / Import requirements
py-env-studio --export <env_name>,requirements.txt
py-env-studio --import-reqs <env_name>,requirements.txt
