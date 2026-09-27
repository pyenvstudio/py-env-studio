import sys
from pathlib import Path

# Add plugins directory to path
plugins_dir = Path.home() / '.py_env_studio' / 'plugins' / 'sample_plugin'
sys.path.insert(0, str(plugins_dir.parent))

print(f"Python path: {sys.path[0]}")
print(f"Plugins dir: {plugins_dir}")

try:
    from sample_plugin import SamplePlugin
    print("✓ Successfully imported SamplePlugin")
    plugin = SamplePlugin()
    metadata = plugin.get_metadata()
    print(f"✓ Plugin: {metadata.name} v{metadata.version}")
    print(f"✓ Entry point: {metadata.entry_point}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
