#!/usr/bin/env python
from nose.tools import assert_almost_equal, assert_equal, assert_true
from genologics.epp import significant_figures as sf

class TestEPP(object):
    def test_significant_figures(self):
        f1 = 0.123
        f2 = 0.456
        f3 = 0.000123
        f4 = 0.000456

        equals = [(sf(f1,1),'0.1'),
                  (sf(f1,2),'0.12'),
                  (sf(f2,2),'0.5'),
                  (sf(f2,2),'0.46'),
                  (sf(f3,1),'0.001'),
                  (sf(f3,2),'0.00012'),
                  (sf(f4,1),'0.0005'),
                  (sf(f4,2),'0.00046')]

        map(lambda t: assert_equal(*t),equals)

