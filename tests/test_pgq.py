
import pgq

from skytools import natsort_key

def test_version():
    assert natsort_key(pgq.__version__) >= natsort_key('3.3')

