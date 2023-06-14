'''
pyATS Library Sample Job File
'''
import os
import logging
from sys import platform
from pyats.easypy import run

logger = logging.getLogger(__name__)

if platform == "darwin":
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "novalue")


def main(runtime):
    test_path = os.path.dirname(os.path.abspath(__file__))

    run(testscript=f"{test_path}/all_tests.py",
        datafile=f"{test_path}/datafiles/datafile.yml")
