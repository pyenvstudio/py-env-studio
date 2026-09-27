from pathlib import Path
import sys

sys.path.insert(0, str(Path.home() / '.py_env_studio' / 'plugins'))

from py_env_studio.core.plugins import PluginManager
import logging

logging.basicConfig(level=logging.INFO)

manager = PluginManager()
manager.set_app_context({
    'app': None, 
    'config': None, 
    'logger': logging.getLogger('test')
})

discovered = manager.discover_plugins()
print(f'Discovered plugins: {discovered}')

try:
    plugin = manager.load_plugin('sample_plugin')
    print(f'Success! Loaded plugin: {plugin.get_metadata().name}')
    print(f'Plugin is enabled: {manager.is_plugin_enabled("sample_plugin")}')
except Exception as e:
    print(f'Failed: {e}')
    import traceback
    traceback.print_exc()
