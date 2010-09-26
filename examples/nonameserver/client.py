# Client that doesn't use the Name Server. Uses URI directly.

import Pyro4

uri = raw_input('Enter the URI of the quote object: ')
quotegen=Pyro4.core.Proxy(uri)
print 'Getting some quotes...'
print quotegen.quote()
print quotegen.quote()
