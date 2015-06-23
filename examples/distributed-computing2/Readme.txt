A simple distributed computing example with "push" model.

There are a handfull of word-counter instances.
Each is able to count the word frequencies in the lines of text given to it.
The counters are registered in the name server using a common name prefix,
which is used by the dispatcher to get a list of all available counters.

The client reads the text (Alice in Wonderland by Lewis Carroll, downloaded from
Project Gutenberg) and hands it off to the counters to determine the word frequencies.

To demonstrate the massive speedup you can potentially get, it first uses just
a single counter to process the full text. Then it does it again but now
uses the dispatcher counter instead - which distributes chunks of the text
across all available counters in parallel.

The actual counter implementation contains a small artificial delay,
this helps dramatize the time saving effect of the parallel processing.


Make sure a name server is running before starting this example.
