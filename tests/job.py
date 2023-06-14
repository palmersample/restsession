'''
pyATS Library Sample Job File
'''
import os
import socket
import logging
from sys import platform
from pyats.datastructures.logic import Or
from genie.harness.main import gRun
from pyats.easypy import run
import sys
from pathlib import Path # if you haven't already done so

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

import all_tests

logger = logging.getLogger(__name__)


if platform == "darwin":
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "novalue")

def main(runtime):
    # webserver_port = get_free_port()
    test_path = os.path.dirname(os.path.abspath(__file__))
    # run(testscript=f"{test_path}/test_code.py",
    #     datafile=f"{test_path}/datafiles/datafile.yml")

    run(testscript=f"{test_path}/all_tests.py",
        datafile=f"{test_path}/datafiles/datafile.yml")


    # run(testscript=f"{test_path}/test_basic_requests.py",
    #     datafile=f"{test_path}/datafiles/datafile.yml")
    #
    # run(testscript=f"{test_path}/test_request_retries.py",
    #     datafile=f"{test_path}/datafiles/datafile.yml")
    #
    # run(testscript=f"{test_path}/test_request_redirects.py",
    #     datafile=f"{test_path}/datafiles/datafile.yml")


    #
    # result = run(testscript="test_code.py",
    #              webserver_port=webserver_port,
    #              input_one="Something first",
    #              input_two="Something else.")

    # gRun(trigger_datafile=f"{test_path}/datafiles/trigger_datafile.yml",
    #      subsection_datafile=f"{test_path}/datafiles/subsection_datafile.yml",
    #      datafile=f"{test_path}/datafiles/datafile.yml",
    #      trigger_uids=Or("test_requests"))
