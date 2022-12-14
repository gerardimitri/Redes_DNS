from http import client
from ipaddress import ip_address
import socket
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
import dnslib
import sys
from dnslib.dns import RR, A
from dnslib import DNSRecord, DNSHeader, DNSQuestion


SOCKET_HOST = "localhost"
SOCKET_PORT = 5300
BUFF_SIZE = 4096
DEBUG = False

cache = {}
dom_list = [None]*100
COUNT = 0

def send_dns_message(address, port, qname = "example.com"):
     # Acá ya no tenemos que crear el encabezado porque dnslib lo hace por nosotros, por default pregunta por el tipo A
     q = DNSRecord.question(qname)
     server_address = (address, port)
     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     try:
         # lo enviamos, hacemos cast a bytes de lo que resulte de la función pack() sobre el mensaje
         sock.sendto(bytes(q.pack()), server_address)
         # En data quedará la respuesta a nuestra consulta
         data, _ = sock.recvfrom(4096)
         # print("This is the data: ", data)
         # le pedimos a dnslib que haga el trabajo de parsing por nosotros 
         d = DNSRecord.parse(data)
     finally:
         sock.close()
     # Ojo que los datos de la respuesta van en en una estructura de datos
     return d

def parse_dns_message(dns_message):
     return DNSRecord.parse(dns_message)

def pack_dns_message(dns_message):
     return dns_message.pack()

def domainToList(domain_name):
     if(domain_name[-1] != "."):
           domain_name = domain_name + "."
     domain = domain_name.split(".")
     domain.reverse()
     #[, cl, uchile, www]
     for i in range(len(domain)):
               domain[i] = domain[i] + "."
     #[., cl., uchile., www.] 
     for i in range(2, len(domain)):
          domain[i] = domain[i] + domain[i-1]
     #[., cl., uchile.cl., www.uchile.cl.]
     return domain

def DNSresolver(domain_name, server_address=("8.8.8.8", 53)):
     domain = domainToList(domain_name)

     for part in domain:
          dnslib_reply = send_dns_message(server_address[0], server_address[1], qname = part)
          number_of_authority_elements = dnslib_reply.header.auth
          number_of_answer_elements = dnslib_reply.header.a
          number_of_additional_elements = dnslib_reply.header.ar
          name_server = ""
          server_ip = ""
          if number_of_answer_elements > 0 and name_server == "":
               first_answer = dnslib_reply.get_a()
               name_server = str(first_answer.get_rname())

          if number_of_additional_elements > 0 and name_server == "":
               additional_records = dnslib_reply.ar 
               first_additional_record = additional_records[0]
               ar_type = QTYPE.get(first_additional_record.rclass) 
               if ar_type == 'A': # si el tipo es 'A' (Address)
                    name_server = str(first_additional_record.rname)  # nombre de dominio             
                    #server_ip = first_additional_record.rdata  # IP asociada

          if number_of_authority_elements > 0 and name_server == "":
               authority_section_list = dnslib_reply.auth  # contiene un total de number_of_authority_elements
               if len(authority_section_list) > 0:
                    authority_section_0_rdata = authority_section_list[0].rdata
                    # si recibimos auth_type = 'SOA' este es un objeto tipo dnslib.dns.SOA
                    if isinstance(authority_section_0_rdata, dnslib.dns.SOA):
                         name_server = str(authority_section_0_rdata.get_mname() ) # servidor de nombre primario

                    elif isinstance(authority_section_0_rdata, dnslib.dns.NS): # si en vez de SOA recibimos un registro tipo NS
                         name_server = str(authority_section_0_rdata)  # entonces authority_section_0_rdata contiene el nombre de dominio del primer servidor de nombre de la lista

          if name_server != "" and DEBUG:
               print(f"(debug) consultando el NS de {part} en {server_address[0]}")
          elif DEBUG:
               print(f"(debug) no se pudo resolver {part}")

          dnslib_reply = send_dns_message(server_address[0], server_address[1], qname = name_server)
          number_of_authority_elements = dnslib_reply.header.auth
          number_of_answer_elements = dnslib_reply.header.a
          number_of_additional_elements = dnslib_reply.header.ar        

          if number_of_answer_elements > 0 and server_ip == "":
               first_answer = dnslib_reply.get_a()
               server_ip = str(first_answer.rdata)

          if number_of_additional_elements > 0 and server_ip == "":
               additional_records = dnslib_reply.ar 
               first_additional_record = additional_records[0]
               ar_type = QTYPE.get(first_additional_record.rclass) 
               if ar_type == 'A': # si el tipo es 'A' (Address)           
                    server_ip = str(first_additional_record.rdata)  # IP asociada

          if server_ip != "" and DEBUG:
               print(f"(debug) consultando {name_server} en {server_ip}")
          elif server_ip == "":
               server_ip = DNSresolver(name_server, ("8.8.8.8", 53))
               if server_ip == "" and DEBUG:
                    print(f"(debug) no se pudo resolver {name_server}")
                    return ""
               elif server_ip == "":
                    return ""
          server_address = (server_ip, 53)

     print(f"{domain_name} -> {server_ip}")
     return server_address[0]

def resolverWithCache(qname):
     # CACHE
     global COUNT
     global cache
     global dom_list
     dom_list[COUNT%100] = qname
     cache_counted = {i:dom_list.count(i) for i in dom_list}
     cache_counted = sorted(cache_counted, key = cache_counted.get, reverse = True)
     top10 = cache_counted[:10]
     if qname in cache:
          print("Cache hit")
          ip_answer = cache[qname]
     else:
          print("Cache miss")
          cache.pop(qname, None)
          ip_answer = str(DNSresolver(qname))
          if qname in top10:
               cache[qname] = ip_answer
     COUNT += 1
     return ip_answer

               
while True:
     resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     resolver_socket.bind((SOCKET_HOST, SOCKET_PORT))
     received, client_address = resolver_socket.recvfrom(BUFF_SIZE)
     received_copy = parse_dns_message(received)
     qname_list = []
     print("Received from client: ", received_copy)
     if DEBUG:
          for arg in sys.argv[1:]:
               qname_list.append(arg)
          for qname in qname_list:
               # CACHE
               ip_answer = resolverWithCache(qname)

               # ip_answer = str(DNSresolver(qname))
               received_copy.add_answer(RR(qname, QTYPE.A, rdata=A(ip_answer)))
               # print("Parsed: ", parse_dns_message(received))
               # print("Packed: ", pack_dns_message(parse_dns_message(received)))

               # print("RESOLVER: " + str(DNSresolver("www.uchile.cl")))
               print("RESOLVER: " + ip_answer)
     else:
          qname = str(received_copy.get_q().get_qname())
          print("QNAME: ", qname)
          # CACHE
          ip_answer = resolverWithCache(qname)
          received_copy.add_answer(RR(qname, QTYPE.A, rdata=A(ip_answer)))
          print("RESOLVER: " + ip_answer)

     print("Received: ", received)
     print("Parsed Received: ", str(received_copy))
     resolver_socket.sendto(pack_dns_message(received_copy), client_address)