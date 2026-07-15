import json
import os
from typing import Dict, Any, Optional
from logger import setup_logger

logger = setup_logger(__name__)

class I18nManager:
    """Manages multi-language support (i18n)"""
    
    _instances: Dict[str, 'I18nManager'] = {}
    _locales: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if not cls._instances:
            cls._instances['default'] = super(I18nManager, cls).__new__(cls)
            cls._instances['default']._load_locales()
        return cls._instances['default']
    
    def _load_locales(self):
        """Load all JSON files from locales directory"""
        locales_dir = "/home/ubuntu/CodingAgentBot/locales"
        if not os.path.exists(locales_dir):
            logger.error(f"Locales directory not found: {locales_dir}")
            return
        
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                try:
                    with open(os.path.join(locales_dir, filename), 'r', encoding='utf-8') as f:
                        self._locales[lang_code] = json.load(f)
                    logger.info(f"Loaded locale: {lang_code}")
                except Exception as e:
                    logger.error(f"Failed to load locale {lang_code}: {e}")
    
    def translate(self, lang: str, key_path: str, **kwargs) -> str:
        """
        Get translated string for given language and key path
        
        Args:
            lang: Language code (e.g., 'en-US', 'ja')
            key_path: Dot-separated key path (e.g., 'SETTING.PANEL_TITLE')
            **kwargs: Variables to format into the string
            
        Returns:
            Translated string or the key path if not found
        """
        # Fallback to en-US if language not found
        locale_data = self._locales.get(lang) or self._locales.get("en-US", {})
        
        keys = key_path.split('.')
        value = locale_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                # If key not found in requested lang, try en-US
                if lang != "en-US":
                    return self.translate("en-US", key_path, **kwargs)
                return key_path
        
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format variable {e} in {key_path}")
                return value
        
        return key_path

# Global instance
i18n = I18nManager()
