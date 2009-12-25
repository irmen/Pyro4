import logging

logging.basicConfig()   # @todo: more sophisticated logging init
logging.root.setLevel(logging.DEBUG)
log=logging.getLogger("Pyro")
log.warn("Pyro log needs better config init")
