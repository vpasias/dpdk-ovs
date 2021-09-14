import subprocess
import ipaddress
from jinja2 import Template
# Python 3.5 script
# subprocess module from stdlib improved in later versions
# https://codingpackets.com/blog/linux-routing-on-the-host-with-frr/

frr_config_template = '''frr version {{ frr_version }}
frr defaults traditional
hostname {{ router_hostname }}
log syslog informational
service integrated-vtysh-config
username iason nopassword
!
interface lo
 ip address {{ local_loopback }}
!
{% if rr_router %}
router bgp 65000
 bgp router-id {{ local_loopback }}
 no bgp default ipv4-unicast
 neighbor LEAF1 peer-group
 neighbor LEAF1 remote-as 65001
 neighbor LEAF1 description Leaf Switch 1
 neighbor LEAF1 capability extended-nexthop
 neighbor LEAF2 peer-group
 neighbor LEAF2 remote-as 65002
 neighbor LEAF2 description Leaf Switch 2
 neighbor LEAF2 capability extended-nexthop 
 neighbor 172.16.11.2 peer-group LEAF1
 neighbor 172.16.21.2 peer-group LEAF1
 neighbor 172.16.12.2 peer-group LEAF2
 neighbor 172.16.22.2 peer-group LEAF2
 !
 address-family ipv4 unicast
  network {{ local_loopback }}/32
  neighbor LEAF1 activate
  neighbor LEAF1 allowas-in
  neighbor LEAF2 activate
  neighbor LEAF2 allowas-in  
 exit-address-family
 !
 address-family ipv6 unicast
  network {{ local_loopback_ipv6 }}/32
  neighbor LEAF1 activate
  neighbor LEAF1 allowas-in
  neighbor LEAF2 activate
  neighbor LEAF2 allowas-in
 exit-address-family
 !
 address-family l2vpn evpn
  neighbor LEAF1 activate
  neighbor LEAF1 allowas-in
  neighbor LEAF2 activate
  neighbor LEAF2 allowas-in 
  advertise-all-vni
 exit-address-family
!
{% endif %}
{% if edge_router %}
vrf vrf_cust1
 vni 4000
 exit-vrf
!
vrf vrf_cust2
 vni 4001
 exit-vrf
!
router bgp {{ as_number }}
 bgp router-id {{ local_loopback }}
 no bgp default ipv4-unicast
 neighbor SPINE peer-group
 neighbor SPINE remote-as 65000
 neighbor SPINE description Internal Fabric Network
 neighbor SPINE capability extended-nexthop
 neighbor 172.16.11.1 peer-group SPINE
 neighbor 172.16.21.1 peer-group SPINE
 neighbor 172.16.12.1 peer-group SPINE
 neighbor 172.16.22.1 peer-group SPINE
 !
 address-family ipv4 unicast
  network {{ local_loopback }}/32
  neighbor SPINE activate
  neighbor SPINE allowas-in
 exit-address-family
 !
 address-family ipv6 unicast
  network {{ local_loopback_ipv6 }}/32
  neighbor SPINE activate
  neighbor SPINE allowas-in
 exit-address-family
 !
 address-family l2vpn evpn
  neighbor SPINE activate
  neighbor SPINE allowas-in 
  advertise-all-vni
 exit-address-family
!
router bgp {{ as_number }} vrf vrf_cust1
 address-family l2vpn evpn
  advertise ipv4 unicast
  advertise ipv6 unicast    
 exit-address-family
!
 address-family ipv4 unicast
  redistribute connected
 exit-address-family
!
 address-family ipv6 unicast
  redistribute connected
 exit-address-family
 ! 
router bgp {{ as_number }} vrf vrf_cust2
 address-family l2vpn evpn
  advertise ipv4 unicast
  advertise ipv6 unicast  
 exit-address-family
!
 address-family ipv4 unicast
  redistribute connected
 exit-address-family
 !
 address-family ipv6 unicast
  redistribute connected
 exit-address-family
 ! 
!
{% endif %}
bfd
!
line vty
!'''
mpls_int_map = {
    'S1': ['br1', 'br2'],
    'S2': ['br1', 'br2'],
    'L1': ['br1', 'br2'],
    'L2': ['br1', 'br2']
    }

def prepend_octet(octet):
    if len(octet) == 0 or len(octet) > 3:
        raise ValueError('incorrect octet {}'.format(octet))
    elif len(octet) == 3:
        return octet
    else:
        while len(octet) < 3:
            octet = '0' + octet
        return octet

frr_ver_run = subprocess.run(['/usr/lib/frr/zebra', '--version'],
                             stdout=subprocess.PIPE)
frr_ver = frr_ver_run.stdout.decode('utf-8')
frr_ver_start = frr_ver.index('version')
frr_ver_end = frr_ver.index('\n', frr_ver_start)
frr_version = frr_ver[frr_ver_start+8:frr_ver_end].strip()
with open('/etc/hostname', 'r', encoding='utf-8') as infile:
    router_hostname = infile.read().strip()

mpls_interfaces = mpls_int_map[router_hostname]
rr_router = True if 'S' in router_hostname else False
edge_router = True if 'L' in router_hostname else False

loopback_addr_run = subprocess.run(['ip', '-br', 'address', 'show', 'lo'],
                                   stdout=subprocess.PIPE)
loopback_addr_list = loopback_addr_run.stdout.decode(
    'utf-8').strip().split(' ')
for address in loopback_addr_list:
    if '/' not in address:
        continue
    try:
        slash = address.index('/')
        local_loopback = ipaddress.ip_address(address[:slash])
    except ValueError:
        continue
    if not local_loopback.is_loopback:
        break

loopback_addr_ipv6_run = subprocess.run(['ip', '-6', '-br', 'address', 'show', 'lo'],
                                   stdout=subprocess.PIPE)
loopback_addr_ipv6_list = loopback_addr_ipv6_run.stdout.decode(
    'utf-8').strip().split(' ')
for address in loopback_addr_ipv6_list:
    if '/' not in address:
        continue
    try:
        slash_ipv6 = address.index('/')
        local_loopback_ipv6 = ipaddress.ip_address(address[:slash_ipv6])
    except ValueError:
        continue
    if not local_loopback_ipv6.is_loopback:
        break

lo_octets = local_loopback.compressed.split('.')
neighbor_loopback = ipaddress.ip_address('127.0.0.27')
if edge_router:
    rr1_loopback = '172.16.250.1'
    rr2_loopback = '172.16.250.2'
    if lo_octets[-1] == '101':
        as_number = 65001        
    elif lo_octets[-1] == '102':
        as_number = 65002
    else:
        raise ValueError('unacceptable loopback address {}'.format(
            local_loopback.compressed))  
if rr_router:
    if lo_octets[-1] == '1':
        neighbor1_last_octet = '101'        
        neighbor2_last_octet = '102'
    elif lo_octets[-1] == '2':
        neighbor1_last_octet = '101'        
        neighbor2_last_octet = '102'    
    else:
        raise ValueError('unacceptable loopback address {}'.format(
            local_loopback.compressed))
    neighbor1_octets = lo_octets[:-1]
    neighbor1_octets.append(neighbor1_last_octet)
    neighbor1_loopback = ipaddress.ip_address('.'.join(neighbor1_octets))
    neighbor2_octets = lo_octets[:-1]
    neighbor2_octets.append(neighbor2_last_octet)
    neighbor2_loopback = ipaddress.ip_address('.'.join(neighbor2_octets))
iso_net = [prepend_octet(x) for x in local_loopback.compressed.split('.')]
iso_net = ''.join(iso_net)
step = 0
for i in range(4, len(iso_net), 4):
    iso_net = iso_net[:i+step] + '.' + iso_net[i+step:]
    step += 1
iso_net = '49.0001.' + iso_net + '.00'
if edge_router:
    template = Template(frr_config_template)
    rendered = template.render(frr_version=frr_version,
                               router_hostname=router_hostname,
                               mpls_interfaces=mpls_interfaces,
                               edge_router=edge_router,
                               local_loopback=local_loopback.compressed,
                               rr1_loopback=rr1_loopback,
                               rr2_loopback=rr2_loopback,
                               as_number=as_number,
                               iso_net=iso_net,
                               local_loopback_ipv6=local_loopback_ipv6
                               )
    with open('frr_generated_config', 'w', encoding='utf-8') as config_file:
        for line in rendered.split('\n'):
            if line.strip():
                config_file.write(line+'\n')
if rr_router:
    template = Template(frr_config_template)
    rendered = template.render(frr_version=frr_version,
                               router_hostname=router_hostname,
                               mpls_interfaces=mpls_interfaces,
                               rr_router=rr_router,
                               local_loopback=local_loopback.compressed,
                               neighbor1_loopback=neighbor1_loopback,
                               neighbor2_loopback=neighbor2_loopback,
                               iso_net=iso_net,
                               local_loopback_ipv6=local_loopback_ipv6
                               )
    with open('frr_generated_config', 'w', encoding='utf-8') as config_file:
        for line in rendered.split('\n'):
            if line.strip():
                config_file.write(line+'\n')
