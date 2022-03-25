import logging





logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s[%(levelname)s][%(filename)s:%(lineno)d] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

__version__ = "1.0.0"