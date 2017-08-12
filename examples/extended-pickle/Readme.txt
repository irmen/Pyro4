Pyro 4.62 added support for the cloudpickle serializer.
Support for dill, another "extended pickle" serializer, has been present since 4.42

The interesting thing about these "extende pickle" serializers is that they can
serialize a lot more Python objects than regular pickle can.
For instance, it is possible to actually serialize actual *functions*.
This means it becomes trivial to let client-defined functions be executed on remote machines,
simply by passing the actual function as an argument.

Be aware of the severe security implications when using this though!
(any client that can connect will be trivially able to execute any code in the server)
