from unittest import TestCase
from tests.mocks import MockIOLoop
from functools import partial


class gr(list):
    def __init__(self, *args):
        super(gr, self).__init__(args)

class seq(gr):
    """define a sequence of possibly asynchronous callables,
       each to be called when the previous one is done"""
    def __call__(self, next):
        try:
            link = self.pop(0)
            link(partial(self.__call__, next))
        except IndexError:
            next()

class par(gr):
    """define a sequence of possibly asynchronous callables,
       to be called in parallel"""

    def __call__(self, next):
        # serve as static variable for the closure
        links = []
        def _cb():
            links.append(True)
            if len(links) == len(self):
                next()

        for link in self:
            link(_cb)


class StrongAssertionError(AssertionError, KeyboardInterrupt):
    """
    In order to traverse exception handlers in ioloop main loop,
    our assertion exception class must subclass either KeyboardInterrupt
    or SystemExit.
    """
    pass

class TornadoTestCase(TestCase):
    failureException = StrongAssertionError

    def setUp(self):
        self.io_loop = MockIOLoop()

    def tearDown(self):
        self.finish()

    def finish(self, *args):
        self.io_loop.stop()

    def execute(self, *args):
        seq(*args)(self.finish)
        self.io_loop.start()

        # We start an ioloop only if the chain has not
        # been executed asynchronously

        
    def expect(self, status=None, headers=(), body=None):
        def _expect(st, hdrs, bdy):
            if status:
                self.assertEquals(status, st)
            for (name, value) in (h.split(': ') for h in headers):
                self.assertTrue(name in hdrs)
                self.assertEquals(value, hdrs[name])
            if body:
                self.assertEquals(body, bdy)
        return _expect
