import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class FileCleanupManager:
    _instance = None
    _cleanup_jobs: Dict[str, datetime] = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FileCleanupManager()
        return cls._instance
    
    def schedule_cleanup(self, filepath: str, minutes: int = 30):
        """Schedule a file for deletion after specified minutes"""
        deletion_time = datetime.now() + timedelta(minutes=minutes)
        self._cleanup_jobs[filepath] = deletion_time
        
        # Start cleanup thread if not already running
        thread = threading.Thread(target=self._cleanup_file, args=(filepath, minutes))
        thread.daemon = True
        thread.start()
    
    def _cleanup_file(self, filepath: str, delay_minutes: int):
        """Delete file after specified delay"""
        try:
            time.sleep(delay_minutes * 60)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up report file: {filepath}")
            self._cleanup_jobs.pop(filepath, None)
        except Exception as e:
            logger.error(f"Error cleaning up file {filepath}: {str(e)}")
