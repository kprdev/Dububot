"""
Container for helpers.
"""

import logging

def configureLogging():
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(name)-20s %(message)s',
        level=logging.INFO
    )
