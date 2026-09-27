from pathlib import Path
import sys
import json

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
    print(f'✓ Loaded plugin: {plugin.get_metadata().name}')
    
    # Execute on_app_start hook
    manager.execute_hook('on_app_start', {'app': None, 'version': '1.0.0'})
    print(f'✓ Executed on_app_start hook')
    
    # Check event log
    events_log = Path.home() / '.py_env_studio' / 'plugins' / 'sample_plugin' / 'events.log'
    if events_log.exists():
        print(f'\n✓ Event log created at: {events_log}')
        with open(events_log) as f:
            events = [json.loads(line) for line in f.readlines()]
        print(f'✓ Total events logged: {len(events)}')
        for event in events[-2:]:
            print(f'  - Hook: {event["hook"]} | Status: {event["status"]}')
    else:
        print(f'✗ Event log not found')
        
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
