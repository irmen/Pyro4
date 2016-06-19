from Pyro4 import expose


class Resource(object):
    pass


@expose
class LaserPrinter(Resource):
    pass


@expose
class MatrixPrinter(Resource):
    pass


@expose
class PhotoPrinter(Resource):
    pass


@expose
class TapeStorage(Resource):
    pass


@expose
class DiskStorage(Resource):
    pass


@expose
class Telephone(Resource):
    pass


@expose
class Faxmachine(Resource):
    pass
