from configparser import ConfigParser

class AppConfig:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.version = self._load_version()

    def _load_version(self):
        config = ConfigParser()
        config.read(self.config_path)
        return config.get('project', 'version', fallback='1.0.0')

    def set_param(self, section: str, option: str, value: str) -> None:
        config = ConfigParser()
        config.read(self.config_path)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        with open(self.config_path, 'w') as config_file:
            config.write(config_file)

    