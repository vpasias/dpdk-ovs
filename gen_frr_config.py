import subprocess
import ipaddress
from jinja2 import Template
# Python 3.5 script
# subprocess module from stdlib improved in later versions

frr_config_template = '''frr version {{ frr_version }}
frr defaults traditional
hostname {{ router_hostname }}
log syslog informational
service integrated-vtysh-config
username iason nopassword
!
{% for interface in mpls_interfaces %}
interface {{ interface }}
 ip ospf area 0
 ip ospf network point-to-point
 ip ospf bfd
 ip ospf hello-interval 10
 ip ospf dead-interval 40
!
{% endfor %}
interface lo
 ip ospf area 0
!
{% if edge_router %}
router bgp 65010
 neighbor {{ neighbor_loopback }} remote-as 65010
 neighbor {{ neighbor_loopback }} update-source {{ local_loopback }}
 !
 address-family ipv4 vpn
  neighbor {{ neighbor_loopback }} activate
 exit-address-family
!
router bgp 65010 vrf vrf_cust1
 !
 address-family ipv4 unicast
  redistribute connected
  label vpn export auto
  rd vpn export 65010:10
  rt vpn both 1:1
  export vpn
  import vpn
 exit-address-family
!
router bgp 65010 vrf vrf_cust2
 !
 address-family ipv4 unicast
  redistribute connected
  label vpn export auto
  rd vpn export 65010:20
  rt vpn both 2:2
  export vpn
  import vpn
 exit-address-family
!
{% endif %}
mpls ldp
 router-id {{ local_loopback }}
 !
 address-family ipv4
  discovery transport-address {{ local_loopback }}
  !
  {% for interface in mpls_interfaces %}
  interface {{ interface }}
  !
  {% endfor %}
 exit-address-family
 !
!
router ospf
 ospf router-id {{ local_loopback }}
 network 172.16.0.0/16 area 0
 router-info area
 fast-reroute ti-lfa
 capability opaque
 mpls-te on
 mpls-te router-address {{ local_loopback }}
 segment-routing on
 segment-routing global-block 16000 23999
 segment-routing node-msd 8
 segment-routing prefix {{ local_loopback }}/32 index {{ sr_index }}
!
bfd
!
line vty
!'''
mpls_int_map = {
    'P1': ['eth1', 'eth2'],
    'PE1': ['eth3'],
    'PE2': ['eth3']
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

if router_hostname == 'PE1':
    sr_index = '11'
elif router_hostname == 'PE2':
    sr_index = '12'
elif router_hostname == 'P1':
    sr_index = '13'

mpls_interfaces = mpls_int_map[router_hostname]
edge_router = True if 'E' in router_hostname else False

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
    if lo_octets[-1] == '1':
        neighbor_last_octet = '2'
    elif lo_octets[-1] == '2':
        neighbor_last_octet = '1'
    elif lo_octets[-1] == '3':
        neighbor_last_octet = '4'
    elif lo_octets[-1] == '4':
        neighbor_last_octet = '3'  
    else:
        raise ValueError('unacceptable loopback address {}'.format(
            local_loopback.compressed))
    neighbor_octets = lo_octets[:-1]
    neighbor_octets.append(neighbor_last_octet)
    neighbor_loopback = ipaddress.ip_address('.'.join(neighbor_octets))
iso_net = [prepend_octet(x) for x in local_loopback.compressed.split('.')]
iso_net = ''.join(iso_net)
step = 0
for i in range(4, len(iso_net), 4):
    iso_net = iso_net[:i+step] + '.' + iso_net[i+step:]
    step += 1
iso_net = '49.0001.' + iso_net + '.00'
template = Template(frr_config_template)
rendered = template.render(frr_version=frr_version,
                           router_hostname=router_hostname,
                           mpls_interfaces=mpls_interfaces,
                           edge_router=edge_router,
                           local_loopback=local_loopback.compressed,
                           neighbor_loopback=neighbor_loopback.compressed,
                           iso_net=iso_net,
                           sr_index=sr_index,
                           local_loopback_ipv6=local_loopback_ipv6
                           )
with open('frr_generated_config', 'w', encoding='utf-8') as config_file:
    for line in rendered.split('\n'):
        if line.strip():
            config_file.write(line+'\n')
