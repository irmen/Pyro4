"""
Tests for some Ironpython peculiarities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import pickle


if sys.platform=="cli":

    class IronPythonWeirdnessTests(unittest.TestCase):
        def testExceptionWithAttrsPickle(self):
            # ironpython doesn't pickle exception attributes
            # see bug report http://ironpython.codeplex.com/workitem/30805
            ex=ValueError("some exception")
            ex.custom_attribute=42
            ex2=pickle.loads(pickle.dumps(ex))
            self.assertTrue(hasattr(ex,"custom_attribute"))
            self.assertFalse(hasattr(ex2,"custom_attribute"))   # custom attribute will be gone after pickling
            self.assertNotEqual(ex2,ex)     # the object won't be equal

        def testExceptionReduce(self):
            # ironpython doesn't pickle exception attributes
            # see bug report http://ironpython.codeplex.com/workitem/30805
            # it could be caused by a malfunctioning __reduce__
            ex=ValueError("some exception")
            ex.custom_attribute=42
            r=ex.__reduce__()
            # the reduce result should be:
            # (ValueError, ("some exception",), {"custom_attribute": 42})
            # but in Ironpython the custom attributes are not returned.
            self.assertNotEqual( (ValueError, ("some exception",), {"custom_attribute": 42}), r)
            self.assertEqual( (ValueError, ("some exception",)), r)

        def testTbFrame(self):
            # there's some stuff missing on traceback frames
            # this prevents a detailed stack trace to be printed by
            # the functions in util.py, for instance.
            def crash():
                a=1
                b=0
                return a//b
            try:
                crash()
            except:
                ex_t, ex_v, ex_tb=sys.exc_info()
                while ex_tb.tb_next:
                    ex_tb=ex_tb.tb_next
                self.assertEqual(None, ex_tb.tb_frame.f_back)   # should not be none... :(


if __name__ == "__main__":
    unittest.main()
