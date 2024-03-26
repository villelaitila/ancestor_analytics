import os
import sys


class VErr(Exception):
    def __init__(self, message, errors=None):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        # Now for your custom code...
        self.errors = errors



def conditional_raise(e):
    if not isinstance(e, Exception):
        e = VErr(e)
    sys.stderr.write(str(e) + '\n')
    if os.getenv('RAISE_EXCEPTION', 'true') == 'true':
        raise e
    else:
        pass  # sys.stderr.write('Could have raised an exception, but RAISE_EXCEPTION prevented.')  # raise Exception(msg)

