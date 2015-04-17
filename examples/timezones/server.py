from __future__ import print_function
import datetime
import pytz
import dateutil.tz
import Pyro4


fmt = '%Y-%m-%d %H:%M:%S %Z%z'

Pyro4.config.SERIALIZERS_ACCEPTED = {"pickle", "marshal", "json", "serpent"}


class Server(object):
    def echo(self, date):
        print("echo: {0}\n  {1} ({2})\n    {3}".format(date, date.tzinfo, type(date.tzinfo), date.strftime(fmt)))
        return date

    def pytz(self):
        tz_nl = pytz.timezone("Europe/Amsterdam")
        return tz_nl.localize(datetime.datetime.now())

    def dateutil(self):
        tz_nl = dateutil.tz.gettz("Europe/Amsterdam")
        return datetime.datetime.now(tz_nl)

# main program

Pyro4.Daemon.serveSimple({
    Server(): "example.timezones"
})
