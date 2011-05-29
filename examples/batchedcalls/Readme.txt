This is an example that shows the batched calls feature.

The example does a lot of method calls on the same proxy object.
It shows the time it takes to do them individually.
Afterwards, it does them again but this time using the batched calls
feature. It prints the time taken and this should be much faster.

It also shows what happens when one of the calls in the batch generates
an error.  (the batch is aborted and the error is raised locally once
the result generator gets to it).
