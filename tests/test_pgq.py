
import pgq

from skytools import natsort_key

from nose.tools import *

def test_version():
    assert_true(natsort_key(pgq.__version__) >= natsort_key('3.3'))

