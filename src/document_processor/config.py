#!filepath document_processor/config.py
class ConverterConfig:
    """Configuration for document conversion processes"""
    
    def __init__(self, config_dict=None):
        """
        Initialize configuration with default values or from provided dictionary
        
        Args:
            config_dict (dict, optional): Dictionary of configuration values
        """
        config_dict = config_dict or {}
          # Image processing options
        self.apply_max_res = config_dict.get("apply_max_res", False)
        self.max_image_res_px = config_dict.get("max_image_res_px", 1200)
        self.exclude_decorative = config_dict.get("exclude_decorative", False)
        self.decorative_threshold_px = config_dict.get("decorative_threshold_px", 50)
        self.embed_small_images = config_dict.get("embed_small_images", False)
        self.small_image_threshold_kb = config_dict.get("small_image_threshold_kb", 50)
        
        # Excel/CSV options
        self.max_rows_display = config_dict.get("max_rows_display", 1000) 
        self.max_columns_display = config_dict.get("max_columns_display", 50)
        
        # Pandoc options
        self.pandoc_toc = config_dict.get("pandoc_toc", False)
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            "apply_max_res": self.apply_max_res,
            "max_image_res_px": self.max_image_res_px,
            "exclude_decorative": self.exclude_decorative,
            "decorative_threshold_px": self.decorative_threshold_px,
            "embed_small_images": self.embed_small_images,
            "small_image_threshold_kb": self.small_image_threshold_kb,
            "max_rows_display": self.max_rows_display,
            "max_columns_display": self.max_columns_display,
            "pandoc_toc": self.pandoc_toc
        }
    
    @classmethod
    def from_dict(cls, config_dict):
        """Create configuration from dictionary"""
        return cls(config_dict)

    def get(self, key, default=None):
        """Get configuration value by key"""
        return getattr(self, key, default)