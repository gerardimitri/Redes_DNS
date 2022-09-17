from http import client
import socket
from dnslib import DNSRecord

SOCKET_HOST = "localhost"
SOCKET_PORT = 5300
BUFF_SIZE = 4096

def send_dns_message(address, port):
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
     for i in range(1, len(domain)):
          domain[i] = domain[i] + "." + domain[i-1]
     for part in domain:
          q = DNSRecord.question(part)
          sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          try:
               sock.sendto(bytes(q.pack()), server_address)
               data, _ = sock.recvfrom(BUFF_SIZE)
               d = DNSRecord.parse(data)
          finally:
               sock.close()
          resource_records = d.rr
          for a in resource_records:
               if(a.rtype == 1):
                    return a.rdata

while True:
     resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
     resolver_socket.bind((SOCKET_HOST, SOCKET_PORT))
     received, client_address = resolver_socket.recvfrom(BUFF_SIZE)

     print("Received: ", received)
     print("Parsed: ", parse_dns_message(received))
     print("Packed: ", pack_dns_message(parse_dns_message(received)))

     print("RESOLVER: " + str(DNSresolver("www.uchile.cl")))
     print("RESOLVER: " + str(DNSresolver(".")))
     break
# print(received)