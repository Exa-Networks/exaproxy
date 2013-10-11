## ExaProxy

ExaProxy is a a high-performance non-caching proxy. It is able to filter HTTP traffic using your favorite programming language.

It is part of Exa Networks' [SurfProtect](http://www.surfprotect.co.uk/) solution.

Exaproxy is used in production since early 2013, and proxies millions of URL per day, one installation sees Gb/s of HTTP traffic, with hundreds of Mb/s per server, and several tens of thousands of connections per machine, but this does not mean our work is finished. We continue to improve it.

## News

Juilly 6th 2013, released ExaProxy 1.1.2

This release fixes one scalability issue when the proxy is processing over several ten of thousand connections, adds support for pre-RFC 2616 syntaxes (used by bad embeded systems) and adds many features (see our [changelog](https://exaproxy.googlecode.com/hg/CHANGELOG))
 
## Features

 * Non-caching HTTP/HTTPS (with CONNECT) Proxy
  * forward, reverse or transparent proxy
  * IPv6 and/or IPv4 support (can act as a 4to6 or 6to4 gateway)
 * High Performance
 * Working with the "upcoming" web services
   * support for unknown HTTP versions
   * websocket and TLS support (Upgrade header support)
 * Traffic interception
   * [SQUID compatible](http://www.squid-cache.org/Doc/config/url_rewrite_program/) interface
   * [ICAP like](http://www.faqs.org/rfcs/rfc3507.html) interface via local program
 * Support for [HAProxy proxy protocol](http://haproxy.1wt.eu/download/1.5/doc/proxy-protocol.txt)
 * Built-in web servers to monitor the proxy via local webpage ( default http://127.0.0.1:8080 )
   * dynamic configuration change
   * running information in json format (/json) 

## Usage

Start ExaProxy on your local machine and point your browser to 127.0.0.1 port 8000

## More Information

Keep up to date, follow *[twitter](https://twitter.com/#!/search/exaproxy)* or the *[google community](https://plus.google.com/u/0/communities/100651429598143540706)*

ExaProxy was born out by necessity. No other open source proxy has the same features [RFC compliance](https://github.com/Exa-Networks/exaproxy/wiki/RFC)

This  [presentation](http://www.uknof.org.uk/uknof22/Mangin-ExaProxy.pdf) explains why other solutions were not suitable.

Development is done on python 2.7. This program has no dependencies on third party libraries and will run out of the box on any Unix system.

Tested with [Co-Advisor](http://coad.measurement-factory.com/). We are failing HTTP/1.0 conversion requirement and responses modifications (which we do not support as we assume that both the client and server are valid HTTP/1.1 implementation).


## Get it

```sh
> wget http://exaproxy.googlecode.com/files/exaproxy-1.1.2.tgz
> tar zxvf exaproxy-1.1.2.tgz
> cd exaproxy-1.1.2
> ./sbin/exaproxy
```

will give you a working proxy on port 3128

```sh
> ./sbin/exaproxy -h
```

will give you a definition of all the configuration options

```sh
> env exaproxy.tcp4.port=8088./sbin/exaproxy -de

exaproxy.tcp4.port='8088'
```
or 
```sh
> export exaproxy_tcp4_port=8088
> ./sbin/exaproxy -de

exaproxy.tcp4.port='8088'
```

To change from the command line and see what options were changed from their default configuration values in the configuration file.
