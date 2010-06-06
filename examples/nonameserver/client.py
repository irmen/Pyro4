# Client that doesn't use the Name Server. Uses URI directly.

import Pyro

uri = raw_input('Enter the URI of the quote object: ')
quotegen=Pyro.core.Proxy(uri)
print 'Getting some quotes...'
print quotegen.quote()
print quotegen.quote()
