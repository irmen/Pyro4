/**
Client side javascript example that talks to Pyro's http gateway.
You can run this with node.js.
**/
var http = require('http');

function obtainCharset (headers) {
  // Find the charset, if specified.
  var charset;
  var contentType = headers['content-type'] || '';
  var matches = contentType.match(/charset=([^;,\r\n]+)/i);
  if (matches && matches[1]) {
    charset = matches[1];
  }
  return charset || 'utf-8';
}

function pyro_call(object, method, callback) {
    http.get("http://localhost:8080/pyro/"+object+"/"+method, function(res) {
        var charset = obtainCharset(res.headers);
        res.setEncoding(charset);
        buffer='';
        res.on('data', function(d) {
            buffer += d.toString();
        });

        res.on('end', function() {
            if(res.statusCode==200) {
                // all was well, process the response data as json
                var parsed = JSON.parse(buffer);
                callback(parsed);
            } else {
                // 404, 500 or some other server error occurred
                console.error("Server returned error response:");
                console.error(buffer);
            }
        });
    }).on('error', function(e) {
        // connection error of some sort
        console.error("ERROR:", e.toString());
    });
}

/*--------- do some pyro calls: ----------*/
pyro_call("Pyro.NameServer", "list", function(response) { 
    console.log("\nLIST--->");
    console.log(JSON.stringify(response, null, 4)); 
});

pyro_call("Pyro.NameServer", "$meta", function(response) { 
    console.log("\nMETA--->");
    console.log(JSON.stringify(response, null, 4)); 
});

pyro_call("Pyro.NameServer", "lookup?name=Pyro.NameServer", function(response) { 
    console.log("\nLOOKUP--->");
    console.log(JSON.stringify(response, null, 4)); 
});
