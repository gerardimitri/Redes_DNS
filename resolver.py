from http import client
from ipaddress import ip_address
import socket
from dnslib import DNSRecord
from dnslib.dns import CLASS, QTYPE
import dnslib
import sys

SOCKET_HOST = "localhost"
SOCKET_PORT = 5300
BUFF_SIZE = 4096

def send_dns_message(address, port, qname = "example.com"):
     # Acá ya no tenemos que crear el encabezado porque dnslib lo hace por nosotros, por default pregunta por el tipo A
     qname = "example.com"
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

# Es dnslib la que sabe como se debe imprimir la estructura, usa el mismo formato que dig, los datos NO vienen en un string gigante, sino en una estructura de datos
example = send_dns_message("8.8.8.8", 53)
print(example)

def DNSresolver(domain_name, server_address=("8.8.8.8", 53)):
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

     # DESCOMENTA ESTO PA CUANDO PRUEBES GERARDO QLO
     #server_ip = ""
     for part in domain:
          dnslib_reply = send_dns_message(server_address[0], server_address[1], qname = part)
          number_of_authority_elements = dnslib_reply.header.auth
          number_of_answer_elements = dnslib_reply.header.a
          number_of_additional_elements = dnslib_reply.header.ar
          name_server = ""
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

          if name_server != "":
               print(f"(debug) consultando el NS de {part} en {name_server}")
          else:
               print(f"(debug) no se pudo resolver {part}")

          dnslib_reply = send_dns_message(server_address[0], server_address[1], qname = name_server)
          number_of_authority_elements = dnslib_reply.header.auth
          number_of_answer_elements = dnslib_reply.header.a
          number_of_additional_elements = dnslib_reply.header.ar
          server_ip = ""

          if(number_of_answer_elements > 0):
               first_answer = dnslib_reply.get_a()
               server_ip = str(first_answer.get_rdata())

          elif number_of_additional_elements > 0:
               additional_records = dnslib_reply.ar 
               first_additional_record = additional_records[0]
               ar_type = QTYPE.get(first_additional_record.rclass) 
               if ar_type == 'A': # si el tipo es 'A' (Address)           
                    server_ip = str(first_additional_record.rdata)  # IP asociada

          if server_ip != "":
               print(f"(debug) consultando {part} en {server_ip}")
          else:
               print(f"(debug) no se pudo resolver {part}")
          server_address[0] = server_ip

     print(f"{domain_name} -> {server_ip}")
     return server_address[0]
          
               
while True:
     resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     resolver_socket.bind((SOCKET_HOST, SOCKET_PORT))
     received, client_address = resolver_socket.recvfrom(BUFF_SIZE)

     domain_name = Z = str(sys.argv[1])

     print("Received: ", received)
     print("Parsed: ", parse_dns_message(received))
     print("Packed: ", pack_dns_message(parse_dns_message(received)))

     print("RESOLVER: " + str(DNSresolver("www.uchile.cl")))
     print("RESOLVER: " + str(DNSresolver(domain_name)))
     break
# print(received)