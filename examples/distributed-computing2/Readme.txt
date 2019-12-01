A simple distributed computing example with "push" model.

There are a handful of word-counter instances.
Each is able to count the word frequencies in the lines of text given to it.
The counters are registered in the name server using a common name prefix,
which is used by the dispatcher to get a list of all available counters.

The client reads the text (Alice in Wonderland by Lewis Carroll, downloaded from
Project Gutenberg) and hands it off to the counters to determine the word frequencies.

To demonstrate the massive speedup you can potentially get, it first uses just
a single counter to process the full text. Then it does it again but now
uses the dispatcher counter instead - which distributes chunks of the text
across all available counters in parallel.

Make sure a name server is running before starting this example.


NOTE:
-----
This particular example is not a "real" distributed calculation because it uses
*threads* to process multiple Pyro calls concurrently. Because of Python's GIL,
threads will NOT run in parallel unless they wait for a signal or are doing I/O.
This is why this example has an artificial timer delay to make the compute calls
not cpu-bound thereby enabling actual parallel execution.

For "true" distributed parallel calculations, have a look at the other
distributed-computing examples.
