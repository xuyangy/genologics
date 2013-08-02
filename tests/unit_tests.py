#!/usr/bin/env python
from nose.tools import assert_almost_equal, assert_equal, assert_true
from genologics.epp import significant_figures as sf

class TestEPP(object):
    def test_significant_figures(self):
        f1 = 0.123
        f2 = 0.456
        f3 = 0.000123
        f4 = 0.000456
        f5 = 123.5123

        equals = [(sf(f1,1),'0.1'),
                  (sf(f1,2),'0.12'),
                  (sf(f2,1),'0.5'),
                  (sf(f2,2),'0.46'),
                  (sf(f3,1),'0.0001'),
                  (sf(f3,2),'0.00012'),
                  (sf(f4,1),'0.0005'),
                  (sf(f4,2),'0.00046'),
                  (sf(f5,2),'1.2e+02'), # This one is not 100%
                  (sf(f5,3),'124'),
                  (sf(f5,4),'123.5')]

        map(lambda t: assert_equal(*t),equals)

