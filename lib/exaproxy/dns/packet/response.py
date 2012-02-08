import convert

class DNSResponseType:
	CLASS = 1   # Internet
	NAME = None
	VALUE = None

	encode_factory = None
	decode_factory = None

	def __init__(self, name, value):
		self.name = name
		self.value = value

	def __str__(self):
		if self.NAME is not None:
			return "%s RESPONSE for %s: %s" % (self.NAME, self.name, self.value)

		return 'DNS DUMMY QUERY'


class DNSAResponseType(DNSResponseType):
	NAME = 'A'
	VALUE = 1

	encode_factory = staticmethod(convert.ipv4_aton)
	decode_factory = staticmethod(convert.ipv4_ntoa)
	
class DNSNSResponseType(DNSResponseType):
	NAME = 'NS'
	VALUE = 2
	
class DNSMDResponseType(DNSResponseType):
	NAME = 'MD'
	VALUE = 3

class DNSMFResponseType(DNSResponseType):
	NAME = 'MF'
	VALUE = 4

class DNSCNAMEResponseType(DNSResponseType):
	NAME = 'CNAME'
	VALUE = 5

class DNSSOAResponseType(DNSResponseType):
	NAME = 'SOA'
	VALUE = 6

class DNSMBResponseType(DNSResponseType):
	NAME = 'MB'
	VALUE = 7

class DNSMGResponseType(DNSResponseType):
	NAME = 'MG'
	VALUE = 8

class DNSMRResponseType(DNSResponseType):
	NAME = 'MR'
	VALUE = 9

class DNSNULLResponseType(DNSResponseType):
	NAME = 'NULL'
	VALUE = 10

class DNSWKSResponseType(DNSResponseType):
	NAME = 'WKS'
	VALUE = 11

class DNSPTRResponseType(DNSResponseType):
	NAME = 'PTR'
	VALUE = 12

class DNSHINFOResponseType(DNSResponseType):
	NAME = 'HINFO'
	VALUE = 13

class DNSMINFOResponseType(DNSResponseType):
	NAME = 'MINFO'
	VALUE = 14

class DNSMXResponseType(DNSResponseType):
	NAME = 'MX'
	VALUE = 15

class DNSTXTResponseType(DNSResponseType):
	NAME = 'TXT'
	VALUE = 16

class DNSRPResponseType(DNSResponseType):
	NAME = 'RP'
	VALUE = 17

class DNSAFSDBResponseType(DNSResponseType):
	NAME = 'AFSDB'
	VALUE = 18

class DNSX25ResponseType(DNSResponseType):
	NAME = 'X25'
	VALUE = 19

class DNSISDNResponseType(DNSResponseType):
	NAME = 'ISDN'
	VALUE = 20

class DNSRTResponseType(DNSResponseType):
	NAME = 'RT'
	VALUE = 21

class DNSNSAPResponseType(DNSResponseType):
	NAME = 'NSAP'
	VALUE = 22

class DNSNSAPPTRResponseType(DNSResponseType):
	NAME = 'NSAPPTR'
	VALUE = 23

class DNSSIGResponseType(DNSResponseType):
	NAME = 'SIG'
	VALUE = 24

class DNSKEYResponseType(DNSResponseType):
	NAME = 'KEY'
	VALUE = 25

class DNSPXResponseType(DNSResponseType):
	NAME = 'PX'
	VALUE = 26

class DNSGPOSResponseType(DNSResponseType):
	NAME = 'GPOS'
	VALUE = 27

class DNSAAAAResponseType(DNSResponseType):
	NAME = 'AAAA'
	VALUE = 28

class DNSLOCResponseType(DNSResponseType):
	NAME = 'LOC'
	VALUE = 29

class DNSNXTResponseType(DNSResponseType):
	NAME = 'NXT'
	VALUE = 30

class DNSEIDResponseType(DNSResponseType):
	NAME = 'EID'
	VALUE = 31

class DNSNIMLOCResponseType(DNSResponseType):
	NAME = 'NIMLOC'
	VALUE = 32

class DNSSRVResponseType(DNSResponseType):
	NAME = 'SRV'
	VALUE = 33

class DNSATMAResponseType(DNSResponseType):
	NAME = 'ATMA'
	VALUE = 34

class DNSNAPTRResponseType(DNSResponseType):
	NAME = 'NAPTR'
	VALUE = 35

class DNSKXResponseType(DNSResponseType):
	NAME = 'KX'
	VALUE = 36

class DNSCERTResponseType(DNSResponseType):
	NAME = 'CERT'
	VALUE = 37

class DNSA6ResponseType(DNSResponseType):
	NAME = 'A6'
	VALUE = 38

class DNSDNAMEResponseType(DNSResponseType):
	NAME = 'DNAME'
	VALUE = 39

class DNSSINKResponseType(DNSResponseType):
	NAME = 'SINK'
	VALUE = 40

class DNSOPTResponseType(DNSResponseType):
	NAME = 'OPT'
	VALUE = 41

class DNSAPLResponseType(DNSResponseType):
	NAME = 'APL'
	VALUE = 42

class DNSDSResponseType(DNSResponseType):
	NAME = 'DS'
	VALUE = 43

class DNSSSHFPResponseType(DNSResponseType):
	NAME = 'SSHFP'
	VALUE = 44

class DNSIPSECKEYResponseType(DNSResponseType):
	NAME = 'IPSECKEY'
	VALUE = 45

class DNSRRSIGResponseType(DNSResponseType):
	NAME = 'RRSIG'
	VALUE = 46

class DNSNSECResponseType(DNSResponseType):
	NAME = 'NSEC'
	VALUE = 47

class DNSDNSKEYResponseType(DNSResponseType):
	NAME = 'DNSKEY'
	VALUE = 48

class DNSDHCIDResponseType(DNSResponseType):
	NAME = 'DHCID'
	VALUE = 49

class DNSNSEC3ResponseType(DNSResponseType):
	NAME = 'NSEC3'
	VALUE = 50

class DNSNSEC3PARAMResponseType(DNSResponseType):
	NAME = 'NSEC3PARAM'
	VALUE = 51

class DNSHIPResponseType(DNSResponseType):
	NAME = 'HIP'
	VALUE = 55

class DNSNINFOResponseType(DNSResponseType):
	NAME = 'NINFO'
	VALUE = 56

class DNSRKEYResponseType(DNSResponseType):
	NAME = 'RKEY'
	VALUE = 57

class DNSTALINKResponseType(DNSResponseType):
	NAME = 'TALINK'
	VALUE = 58

class DNSSPFResponseType(DNSResponseType):
	NAME = 'SPF'
	VALUE = 99

class DNSMFResponseType(DNSResponseType):
	NAME = 'UINFO'
	VALUE = 100

class DNSUIDResponseType(DNSResponseType):
	NAME = 'UID'
	VALUE = 101

class DNSGIDResponseType(DNSResponseType):
	NAME = 'GID'
	VALUE = 102

class DNSUNSPECResponseType(DNSResponseType):
	NAME = 'UNSPEC'
	VALUE = 103

class DNSTKEYResponseType(DNSResponseType):
	NAME = 'TKEY'
	VALUE = 249

class DNSTSIGResponseType(DNSResponseType):
	NAME = 'TSIG'
	VALUE = 250

class DNSIXFRResponseType(DNSResponseType):
	NAME = 'IXFR'
	VALUE = 251

class DNSAXFRResponseType(DNSResponseType):
	NAME = 'AXFR'
	VALUE = 252

class DNSMAILBResponseType(DNSResponseType):
	NAME = 'MAILB'
	VALUE = 253

class DNSMAILAResponseType(DNSResponseType):
	NAME = 'MAILA'
	VALUE = 254

class DNSSTARResponseType(DNSResponseType):
	NAME = 'STAR'
	VALUE = 255

class DNSDNSSECAUTHORITIESResponseType(DNSResponseType):
	NAME = 'DNSSECAUTHORITIES'
	VALUE = 32768

class DNSDNSSECLOOKASIDEResponseType(DNSResponseType):
	NAME = 'DNSSECLOOKASIDE'
	VALUE = 32769
