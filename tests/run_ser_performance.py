"""
Prints a comparison between different serializers.
Compares results based on size of the output, and time taken to (de)serialize.
"""

from __future__ import print_function
from timeit import default_timer as perf_timer
import sys
import datetime
import decimal
import uuid
import Pyro4.util
import Pyro4.errors
import Pyro4.core


data = {
    "bytes": b"0123456789abcdefghijklmnopqrstuvwxyz" * 2000,
    "bytearray": bytearray(b"0123456789abcdefghijklmnopqrstuvwxyz") * 2000,
    "str": "\"0123456789\"\n'abcdefghijklmnopqrstuvwxyz'\t" * 2000,
    "unicode": u"abcdefghijklmnopqrstuvwxyz\u20ac\u20ac\u20ac\u20ac\u20ac" * 2000,
    "int": [123456789] * 1000,
    "double": [12345.987654321] * 1000,
    "long": [123456789123456789123456789123456789] * 1000,
    "tuple": [(x * x, "tuple", (300, 400, (500, 600, (x * x, x * x)))) for x in range(200)],
    "list": [[x * x, "list", [300, 400, [500, 600, [x * x]]]] for x in range(200)],
    "set": set(x * x for x in range(1000)),
    "dict": {str(i * i): {str(1000 + j): chr(j + 65) for j in range(5)} for i in range(100)},
    "exception": [ZeroDivisionError("test exeception", x * x) for x in range(1000)],
    "class": [Pyro4.core.URI("PYRO:obj@addr:9999") for x in range(1000)],
    "datetime": [datetime.datetime.now() for x in range(1000)],
    "complex": [complex(x + x, x * x) for x in range(1000)],
    "decimal": [decimal.Decimal("1122334455667788998877665544332211.9876543212345678987654321123456789") for x in range(1000)],
    "uuid": uuid.uuid4()
}

no_result = 9999999999


def run():
    results = {}
    number = 10
    repeat = 3
    for serializername, ser in Pyro4.util._serializers.items():
        print("\nserializer:", serializername)
        results[serializername] = {"sizes": {}, "ser-times": {}, "deser-times": {}}
        for key in sorted(data):
            print(key, end="; ")
            sys.stdout.flush()
            try:
                serialized = ser.dumps(data[key])
            except (TypeError, ValueError, OverflowError, Pyro4.errors.SerializeError) as x:
                print("error!")
                print(x, key)
                results[serializername]["sizes"][key] = no_result
                results[serializername]["ser-times"][key] = no_result
                results[serializername]["deser-times"][key] = no_result
            else:
                results[serializername]["sizes"][key] = len(serialized)
                durations_ser = []
                durations_deser = []
                serialized_data = ser.dumps(data[key])
                for _ in range(repeat):
                    start = perf_timer()
                    for _ in range(number):
                        ser.dumps(data[key])
                    durations_ser.append(perf_timer() - start)
                for _ in range(repeat):
                    start = perf_timer()
                    for _ in range(number):
                        ser.loads(serialized_data)
                    durations_deser.append(perf_timer() - start)
                duration_ser = min(durations_ser)
                duration_deser = min(durations_deser)
                results[serializername]["ser-times"][key] = round(duration_ser * 1e6 / number, 2)
                results[serializername]["deser-times"][key] = round(duration_deser * 1e6 / number, 2)
        print()
    return results


def tables_size(results):
    print("\nSIZE RESULTS\n")
    sizes_per_datatype = {}
    for ser in results:
        for datatype in results[ser]["sizes"]:
            size = results[ser]["sizes"][datatype]
            if datatype not in sizes_per_datatype:
                sizes_per_datatype[datatype] = []
            sizes_per_datatype[datatype].append((size, ser))
    sizes_per_datatype = {datatype: sorted(sizes) for datatype, sizes in sizes_per_datatype.items()}
    for dt in sorted(sizes_per_datatype):
        print(dt)
        for pos, (size, serializer) in enumerate(sizes_per_datatype[dt]):
            if size == no_result:
                size = "unsupported"
            else:
                size = "%8d" % size
            print(" %2d: %-8s  %s" % (pos + 1, serializer, size))
    print()


def tables_speed(results, what_times, header):
    print("\n%s\n" % header)
    durations_per_datatype = {}
    for ser in results:
        for datatype in results[ser]["sizes"]:
            duration = results[ser][what_times][datatype]
            if datatype not in durations_per_datatype:
                durations_per_datatype[datatype] = []
            durations_per_datatype[datatype].append((duration, ser))
    durations_per_datatype = {datatype: sorted(durations) for datatype, durations in durations_per_datatype.items()}
    for dt in sorted(durations_per_datatype):
        print(dt)
        for pos, (duration, serializer) in enumerate(durations_per_datatype[dt]):
            if duration == no_result:
                duration = "unsupported"
            else:
                duration = "%8d" % duration
            print(" %2d: %-8s  %s" % (pos + 1, serializer, duration))
    print()


if __name__ == "__main__":
    results = run()
    tables_size(results)
    tables_speed(results, "ser-times", "SPEED RESULTS (SERIALIZATION)")
    tables_speed(results, "deser-times", "SPEED RESULTS (DESERIALIZATION)")
