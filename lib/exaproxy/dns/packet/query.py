class DNSQueryType:
	CLASS = 1   # Internet
	NAME = None
	VALUE = None

	def __init__(self, name):
		self.name = name

	def __str__(self):
		if self.NAME is not None:
			return "%s REQUEST for %s" % (self.NAME, self.name)

		return 'DNS DUMMY QUERY'


class DNSAQueryType(DNSQueryType):
	NAME = 'A'
	VALUE = 1
	
class DNSNSQueryType(DNSQueryType):
	NAME = 'NS'
	VALUE = 2
	
class DNSMDQueryType(DNSQueryType):
	NAME = 'MD'
	VALUE = 3

class DNSMFQueryType(DNSQueryType):
	NAME = 'MF'
	VALUE = 4

class DNSCNAMEQueryType(DNSQueryType):
	NAME = 'CNAME'
	VALUE = 5

class DNSSOAQueryType(DNSQueryType):
	NAME = 'SOA'
	VALUE = 6

class DNSMBQueryType(DNSQueryType):
	NAME = 'MB'
	VALUE = 7

class DNSMGQueryType(DNSQueryType):
	NAME = 'MG'
	VALUE = 8

class DNSMRQueryType(DNSQueryType):
	NAME = 'MR'
	VALUE = 9

class DNSNULLQueryType(DNSQueryType):
	NAME = 'NULL'
	VALUE = 10

class DNSWKSQueryType(DNSQueryType):
	NAME = 'WKS'
	VALUE = 11

class DNSPTRQueryType(DNSQueryType):
	NAME = 'PTR'
	VALUE = 12

class DNSHINFOQueryType(DNSQueryType):
	NAME = 'HINFO'
	VALUE = 13

class DNSMINFOQueryType(DNSQueryType):
	NAME = 'MINFO'
	VALUE = 14

class DNSMXQueryType(DNSQueryType):
	NAME = 'MX'
	VALUE = 15

class DNSTXTQueryType(DNSQueryType):
	NAME = 'TXT'
	VALUE = 16

class DNSRPQueryType(DNSQueryType):
	NAME = 'RP'
	VALUE = 17

class DNSAFSDBQueryType(DNSQueryType):
	NAME = 'AFSDB'
	VALUE = 18

class DNSX25QueryType(DNSQueryType):
	NAME = 'X25'
	VALUE = 19

class DNSISDNQueryType(DNSQueryType):
	NAME = 'ISDN'
	VALUE = 20

class DNSRTQueryType(DNSQueryType):
	NAME = 'RT'
	VALUE = 21

class DNSNSAPQueryType(DNSQueryType):
	NAME = 'NSAP'
	VALUE = 22

class DNSNSAPPTRQueryType(DNSQueryType):
	NAME = 'NSAPPTR'
	VALUE = 23

class DNSSIGQueryType(DNSQueryType):
	NAME = 'SIG'
	VALUE = 24

class DNSKEYQueryType(DNSQueryType):
	NAME = 'KEY'
	VALUE = 25

class DNSPXQueryType(DNSQueryType):
	NAME = 'PX'
	VALUE = 26

class DNSGPOSQueryType(DNSQueryType):
	NAME = 'GPOS'
	VALUE = 27

class DNSAAAAQueryType(DNSQueryType):
	NAME = 'AAAA'
	VALUE = 28

class DNSLOCQueryType(DNSQueryType):
	NAME = 'LOC'
	VALUE = 29

class DNSNXTQueryType(DNSQueryType):
	NAME = 'NXT'
	VALUE = 30

class DNSEIDQueryType(DNSQueryType):
	NAME = 'EID'
	VALUE = 31

class DNSNIMLOCQueryType(DNSQueryType):
	NAME = 'NIMLOC'
	VALUE = 32

class DNSSRVQueryType(DNSQueryType):
	NAME = 'SRV'
	VALUE = 33

class DNSATMAQueryType(DNSQueryType):
	NAME = 'ATMA'
	VALUE = 34

class DNSNAPTRQueryType(DNSQueryType):
	NAME = 'NAPTR'
	VALUE = 35

class DNSKXQueryType(DNSQueryType):
	NAME = 'KX'
	VALUE = 36

class DNSCERTQueryType(DNSQueryType):
	NAME = 'CERT'
	VALUE = 37

class DNSA6QueryType(DNSQueryType):
	NAME = 'A6'
	VALUE = 38

class DNSDNAMEQueryType(DNSQueryType):
	NAME = 'DNAME'
	VALUE = 39

class DNSSINKQueryType(DNSQueryType):
	NAME = 'SINK'
	VALUE = 40

class DNSOPTQueryType(DNSQueryType):
	NAME = 'OPT'
	VALUE = 41

class DNSAPLQueryType(DNSQueryType):
	NAME = 'APL'
	VALUE = 42

class DNSDSQueryType(DNSQueryType):
	NAME = 'DS'
	VALUE = 43

class DNSSSHFPQueryType(DNSQueryType):
	NAME = 'SSHFP'
	VALUE = 44

class DNSIPSECKEYQueryType(DNSQueryType):
	NAME = 'IPSECKEY'
	VALUE = 45

class DNSRRSIGQueryType(DNSQueryType):
	NAME = 'RRSIG'
	VALUE = 46

class DNSNSECQueryType(DNSQueryType):
	NAME = 'NSEC'
	VALUE = 47

class DNSDNSKEYQueryType(DNSQueryType):
	NAME = 'DNSKEY'
	VALUE = 48

class DNSDHCIDQueryType(DNSQueryType):
	NAME = 'DHCID'
	VALUE = 49

class DNSNSEC3QueryType(DNSQueryType):
	NAME = 'NSEC3'
	VALUE = 50

class DNSNSEC3PARAMQueryType(DNSQueryType):
	NAME = 'NSEC3PARAM'
	VALUE = 51

class DNSHIPQueryType(DNSQueryType):
	NAME = 'HIP'
	VALUE = 55

class DNSNINFOQueryType(DNSQueryType):
	NAME = 'NINFO'
	VALUE = 56

class DNSRKEYQueryType(DNSQueryType):
	NAME = 'RKEY'
	VALUE = 57

class DNSTALINKQueryType(DNSQueryType):
	NAME = 'TALINK'
	VALUE = 58

class DNSSPFQueryType(DNSQueryType):
	NAME = 'SPF'
	VALUE = 99

class DNSMFQueryType(DNSQueryType):
	NAME = 'UINFO'
	VALUE = 100

class DNSUIDQueryType(DNSQueryType):
	NAME = 'UID'
	VALUE = 101

class DNSGIDQueryType(DNSQueryType):
	NAME = 'GID'
	VALUE = 102

class DNSUNSPECQueryType(DNSQueryType):
	NAME = 'UNSPEC'
	VALUE = 103

class DNSTKEYQueryType(DNSQueryType):
	NAME = 'TKEY'
	VALUE = 249

class DNSTSIGQueryType(DNSQueryType):
	NAME = 'TSIG'
	VALUE = 250

class DNSIXFRQueryType(DNSQueryType):
	NAME = 'IXFR'
	VALUE = 251

class DNSAXFRQueryType(DNSQueryType):
	NAME = 'AXFR'
	VALUE = 252

class DNSMAILBQueryType(DNSQueryType):
	NAME = 'MAILB'
	VALUE = 253

class DNSMAILAQueryType(DNSQueryType):
	NAME = 'MAILA'
	VALUE = 254

class DNSSTARQueryType(DNSQueryType):
	NAME = 'STAR'
	VALUE = 255

class DNSDNSSECAUTHORITIESQueryType(DNSQueryType):
	NAME = 'DNSSECAUTHORITIES'
	VALUE = 32768

class DNSDNSSECLOOKASIDEQueryType(DNSQueryType):
	NAME = 'DNSSECLOOKASIDE'
	VALUE = 32769
