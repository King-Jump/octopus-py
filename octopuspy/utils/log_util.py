""" utilities for logger
"""
import os
import logging
import logging.handlers

def _init_log_dir(proj_dir):
    log_dir = os.path.join(proj_dir, 'log')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

def create_logger(proj_dir, log_file, log_name, backup_cnt=10):
    """ create logger """
    _init_log_dir(proj_dir)
    handler = logging.handlers.RotatingFileHandler(
        os.path.join(proj_dir, 'log', log_file),
        maxBytes=50 * 1024 * 1024,
        backupCount=backup_cnt)
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s %(filename)s:%(lineno)d - %(message)s'))
    logger = logging.getLogger(log_name)
    logger.setLevel('DEBUG') # DEBUG ,INFO
    logger.addHandler(handler)
    return logger
