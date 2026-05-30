import logging
from pathlib import Path

def setup_logger():
    log_file_path = Path("logs/app.log")
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("app_logger")
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', 
                                      datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
    return logger

logger = setup_logger()