from __future__ import print_function
import Pyro4
import datetime

fmt = '%Y-%m-%d %H:%M:%S %Z%z'

print("local time without timezone: ", datetime.datetime.now().strftime(fmt))


def test():
    with Pyro4.core.Proxy("PYRONAME:example.timezones") as serv:
        print("\nFIRST: no timezone")
        date1 = serv.echo(datetime.datetime.now())
        print("{0}\n  {1} ({2})".format(date1, repr(date1), type(date1)))
        if hasattr(date1, "tzinfo"):
            print("    tzinfo =", date1.tzinfo)
        else:
            print("    no tzinfo attribute")

        print("\nSECOND: PyTz timezones")
        date1 = serv.pytz()
        assert isinstance(date1.tzinfo, datetime.tzinfo)
        print("{0}\n  {1} ({2})\n    {3}".format(date1, date1.tzinfo, type(date1.tzinfo), date1.strftime(fmt)))
        date2 = serv.echo(date1)
        print("{0}\n  {1} ({2})\n    {3}".format(date2, date2.tzinfo, type(date2.tzinfo), date2.strftime(fmt)))
        assert date1 == date2

        print("\nTHIRD: DateUtil timezones")
        date1 = serv.dateutil()
        assert isinstance(date1.tzinfo, datetime.tzinfo)
        print("{0}\n  {1} ({2})\n    {3}".format(date1, date1.tzinfo, type(date1.tzinfo), date1.strftime(fmt)))
        date2 = serv.echo(date1)
        print("{0}\n  {1} ({2})\n    {3}".format(date2, date2.tzinfo, type(date2.tzinfo), date2.strftime(fmt)))
        assert date1 == date2


# pickle.
print("\n******* pickle *******")
Pyro4.config.SERIALIZER = "pickle"
try:
    test()
except:
    import traceback
    traceback.print_exc()

# serpent.
print("\n******* serpent *******")
Pyro4.config.SERIALIZER = "serpent"
try:
    test()
except:
    import traceback
    traceback.print_exc()

# json.
print("\n******* json *******")
Pyro4.config.SERIALIZER = "json"
try:
    test()
except:
    import traceback
    traceback.print_exc()

# marshal.
print("\n******* marshal *******")
Pyro4.config.SERIALIZER = "marshal"
try:
    test()
except:
    import traceback
    traceback.print_exc()

