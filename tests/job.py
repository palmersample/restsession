'''
pyATS Library Sample Job File
'''
import os
import logging
import sys
from pyats.easypy import run
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

# Import the main package restsession to make classes available for tests
import restsession  # noqa: E402,F401

logger = logging.getLogger(__name__)

logger.error("System path from job.py:\n%s\n", sys.path)

if sys.platform == "darwin":
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "novalue")


def main(runtime):
    test_path = os.path.dirname(os.path.abspath(__file__))

    run(testscript=f"{test_path}/all_tests.py",
        datafile=f"{test_path}/datafiles/datafile.yml")
