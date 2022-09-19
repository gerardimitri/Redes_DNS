from http import client
from ipaddress import ip_address
import socket
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
import dnslib
import sys
from dnslib.dns import RR, A
from dnslib import DNSRecord, DNSHeader, DNSQuestion

# # Modificar el mensaje de pregunta (opción 1)
# dns_query.add_answer(RR(qname, QTYPE.A, rdata=A(ip_answer)))

# # Modificar el mensaje de pregunta (opción 2)
# dns_query.add_answer(*RR.fromZone("{} A {}".format(qname, ip_answer)))

# # Crear un nuevo mensaje que contenga la pregunta y la respuesta
# dns_answer = DNSRecord(id=ans_id, qr=1, aa=1, ra=0, q=DNSQuestion(qname), a=RR(qname, rdata=A(ip_answer)))


SOCKET_HOST = "localhost"
SOCKET_PORT = 5300
BUFF_SIZE = 4096

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
         print("This is the data: ", data)
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
                    server_ip = first_additional_record.rdata  # IP asociada

          if number_of_authority_elements > 0 and name_server == "":
               authority_section_list = dnslib_reply.auth  # contiene un total de number_of_authority_elements
               if len(authority_section_list) > 0:
                    authority_section_0_rdata = authority_section_list[0].rdata
                    # si recibimos auth_type = 'SOA' este es un objeto tipo dnslib.dns.SOA
                    if isinstance(authority_section_0_rdata, dnslib.dns.SOA):
                         name_server = str(authority_section_0_rdata.get_mname() ) # servidor de nombre primario

                    elif isinstance(authority_section_0_rdata, dnslib.dns.NS): # si en vez de SOA recibimos un registro tipo NS
                         name_server = str(authority_section_0_rdata)  # entonces authority_section_0_rdata contiene el nombre de dominio del primer servidor de nombre de la lista

          if name_server != "":
               print(f"(debug) consultando el NS de {part} en {name_server}")
          else:
               print(f"(debug) no se pudo resolver {part}")

          dnslib_reply = send_dns_message(server_address[0], server_address[1], qname = name_server)
          number_of_authority_elements = dnslib_reply.header.auth
          number_of_answer_elements = dnslib_reply.header.a
          number_of_additional_elements = dnslib_reply.header.ar

          if number_of_answer_elements > 0 and server_ip == "":
               first_answer = dnslib_reply.get_a()
               server_ip = str(first_answer.rdata)

          elif number_of_additional_elements > 0 and server_ip == "":
               additional_records = dnslib_reply.ar 
               first_additional_record = additional_records[0]
               ar_type = QTYPE.get(first_additional_record.rclass) 
               if ar_type == 'A': # si el tipo es 'A' (Address)           
                    server_ip = str(first_additional_record.rdata)  # IP asociada

          if server_ip != "":
               print(f"(debug) consultando {name_server} en {server_ip}")
          else:
               print(f"(debug) no se pudo resolver {name_server}")
          server_address = (server_ip, 53)

     print(f"{domain_name} -> {server_ip}")
     return server_address[0]
          
               
while True:
     resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     resolver_socket.bind((SOCKET_HOST, SOCKET_PORT))
     received, client_address = resolver_socket.recvfrom(BUFF_SIZE)

     qname = str(sys.argv[1])

     received_copy = parse_dns_message(received)
     print("Received: ", received)
     print("Parsed Received: ", str(received_copy))

     # # CACHE
     # dom_list[COUNT%100] = qname
     # cache_counted = {i:dom_list.count(i) for i in dom_list}
     # cache_counted = sorted(cache_counted, key = cache_counted.get, reverse = True)
     # top10 = cache_counted[:10]
     # if qname in cache:
     #      print("Cache hit")
     #      ip_answer = cache[qname]
     # else:
     #      print("Cache miss")
     #      cache.pop(qname, None)
     #      ip_answer = str(DNSresolver(qname))
     #      if qname in top10:
     #           cache[qname] = ip_answer
     # COUNT += 1

     ip_answer = str(DNSresolver(qname))
     received_copy.add_answer(RR(qname, QTYPE.A, rdata=A(ip_answer)))
     # print("Parsed: ", parse_dns_message(received))
     # print("Packed: ", pack_dns_message(parse_dns_message(received)))

     # print("RESOLVER: " + str(DNSresolver("www.uchile.cl")))
     resolver_socket.sendto(pack_dns_message(received_copy), client_address)
     print("RESOLVER: " + ip_answer)
     

     break