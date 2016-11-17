import Pyro4
from Pyro4.naming import type_meta

from resources import LaserPrinter, MatrixPrinter, PhotoPrinter, TapeStorage, DiskStorage, Telephone, Faxmachine


# register various objects with some metadata describing their resource class
ns = Pyro4.locateNS()
d = Pyro4.Daemon()
uri = d.register(LaserPrinter)
ns.register("example.resource.laserprinter", uri,
            metadata=type_meta(LaserPrinter) | {"resource:printer", "performance:fast"})
uri = d.register(MatrixPrinter)
ns.register("example.resource.matrixprinter", uri,
            metadata=type_meta(MatrixPrinter) | {"resource:printer", "performance:slow"})
uri = d.register(PhotoPrinter)
ns.register("example.resource.photoprinter", uri,
            metadata=type_meta(PhotoPrinter) | {"resource:printer", "performance:slow"})
uri = d.register(TapeStorage)
ns.register("example.resource.tapestorage", uri,
            metadata=type_meta(TapeStorage) | {"resource:storage", "performance:slow"})
uri = d.register(DiskStorage)
ns.register("example.resource.diskstorage", uri,
            metadata=type_meta(DiskStorage) | {"resource:storage", "performance:fast"})
uri = d.register(Telephone)
ns.register("example.resource.telephone", uri,
            metadata=type_meta(Telephone) | {"resource:communication"})
uri = d.register(Faxmachine)
ns.register("example.resource.faxmachine", uri,
            metadata=type_meta(Faxmachine) | {"resource:communication"})


# check that the name server is actually capable of storing metadata
uri, metadata = ns.lookup("example.resource.laserprinter", return_metadata=True)
if not metadata:
    raise NameError("The name server doesn't support storing metadata. Check its storage type.")


# list all registrations with their metadata
entries = ns.list(return_metadata=True)
for name in entries:
    uri, metadata = entries[name]
    print(name)
    print("   uri:", uri)
    print("   meta:", ", ".join(metadata))
    print()


# query for various metadata
print("\nall storage:")
devices = ns.list(metadata_all={"resource:storage"})
for name, uri in devices.items():
    print("   {} -> {}".format(name, uri))

print("\nall FAST printers:")
devices = ns.list(metadata_all={"resource:printer", "performance:fast"})
for name, uri in devices.items():
    print("   {} -> {}".format(name, uri))

print("\nall storage OR communication devices :")
devices = ns.list(metadata_any={"resource:storage", "resource:communication"})
for name, uri in devices.items():
    print("   {} -> {}".format(name, uri))

# upgrade the photo printer
uri, meta = ns.lookup("example.resource.photoprinter", return_metadata=True)
meta = set(meta)
meta.discard("performance:slow")
meta.add("performance:fast")
ns.set_metadata("example.resource.photoprinter", meta)

print("\nall FAST printers (after photoprinter upgrade):")
devices = ns.list(metadata_all={"resource:printer", "performance:fast"})
for name, uri in devices.items():
    print("   {} -> {}".format(name, uri))

print("\nall resource types:")
devices = ns.list(metadata_all={"class:resources.Resource"})
for name, uri in devices.items():
    print("   {} -> {}".format(name, uri))


print("\n\nPYROMETA protocol for easy yellow-pages lookup:\n")
nameserver = Pyro4.Proxy("PYROMETA:class:Pyro4.naming.NameServer")
print("Proxy to look up 'any nameserver' via its class metadata:")
print("    ", nameserver)
nameserver._pyroBind()
print("Proxy for 'any namesever' bound to candidate:")
print("    ", nameserver._pyroUri)
printer = Pyro4.Proxy("PYROMETA:resource:printer,performance:slow")
print("Proxy for 'any slow printer':")
print("    ", printer)
print("(this example doesn't actually implement these objects so we leave it at that)")
