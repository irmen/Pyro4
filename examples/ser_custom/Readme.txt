Shows the use of the serializer hooks to be able to transfer custom classes
via Pyro (without using the pickle serializer).
If you don't use the serializer hooks, the code will crash with a
SerializeError: unsupported serialized class, but now, it will happily
transfer your object using the custom serialization hooks.

It is recommended to avoid using these hooks if possible, there's a security risk
to create arbitrary objects from serialized data that is received from untrusted sources.
