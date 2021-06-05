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
{% if rr_router %}
router bgp 65010
 bgp router-id {{ local_loopback }}
 bgp log-neighbor-changes
 neighbor {{ neighbor1_loopback }} remote-as 65010
 neighbor {{ neighbor1_loopback }} update-source {{ local_loopback }}
 neighbor {{ neighbor2_loopback }} remote-as 65010
 neighbor {{ neighbor2_loopback }} update-source {{ local_loopback }}
 !
 address-family ipv4 unicast
  no neighbor {{ neighbor1_loopback }} activate
  no neighbor {{ neighbor2_loopback }} activate
 exit-address-family
 !
 address-family l2vpn evpn
  neighbor {{ neighbor1_loopback }} activate
  neighbor {{ neighbor1_loopback }} route-reflector-client
  neighbor {{ neighbor2_loopback }} activate
  neighbor {{ neighbor2_loopback }} route-reflector-client
 exit-address-family
!
{% endif %}
{% if ledge_router %}
vrf vrf_cust1
 vni 4000
 exit-vrf
!
vrf vrf_cust2
 vni 4001
 exit-vrf
!
router bgp 65010
 bgp router-id {{ local_loopback }}
 coalesce-time 1000
 neighbor {{ rr1_loopback }} remote-as 65010
 neighbor {{ rr1_loopback }} update-source {{ local_loopback }}
 neighbor {{ rr2_loopback }} remote-as 65010
 neighbor {{ rr2_loopback }} update-source {{ local_loopback }}
 !
 address-family ipv4 unicast
  no neighbor {{ rr1_loopback }} activate
  no neighbor {{ rr2_loopback }} activate
 exit-address-family
 !
 address-family l2vpn evpn
  neighbor {{ rr1_loopback }} activate
  neighbor {{ rr2_loopback }} activate
  advertise-all-vni
  advertise ipv4 unicast
 exit-address-family
!
router bgp 65010 vrf vrf_cust1
 address-family l2vpn evpn
  advertise ipv4 unicast
 exit-address-family
!
 address-family ipv4 unicast
  redistribute connected
 exit-address-family
!
router bgp 65010 vrf vrf_cust2
 address-family l2vpn evpn
  advertise ipv4 unicast
 exit-address-family
!
 address-family ipv4 unicast
  redistribute connected
 exit-address-family
 !
!
{% endif %}
{% if pedge_router %}
router bgp 65020
 neighbor {{ neighbor_loopback }} remote-as 65020
 neighbor {{ neighbor_loopback }} update-source {{ local_loopback }}
 !
 address-family ipv4 vpn
  neighbor {{ neighbor_loopback }} activate
 exit-address-family
!
router bgp 65020 vrf vrf_cust3
 !
 address-family ipv4 unicast
  redistribute connected
  label vpn export auto
  rd vpn export 65020:10
  rt vpn both 1:1
  export vpn
  import vpn
 exit-address-family
!
router bgp 65020 vrf vrf_cust4
 !
 address-family ipv4 unicast
  redistribute connected
  label vpn export auto
  rd vpn export 65020:20
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
    'S1': ['br1', 'br2', 'br3', 'br4', 'br5', 'br6', 'br7'],
    'S2': ['br1', 'br2', 'br3', 'br4', 'br5', 'br6', 'br7'],
    'X1': ['br1', 'br2', 'br3', 'br4'],
    'X2': ['br1', 'br2', 'br3', 'br4'],
    'LE1': ['br1', 'br2', 'br3', 'br4'],
    'LE2': ['br1', 'br2', 'br3', 'br4'],
    'PE1': ['br1', 'br2', 'br3', 'br4'],
    'PE2': ['br1', 'br2', 'br3', 'br4'] 
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

if router_hostname == 'S1':
    sr_index = '1011'
elif router_hostname == 'S2':
    sr_index = '1012'
elif router_hostname == 'X1':
    sr_index = '1013'
elif router_hostname == 'X2':
    sr_index = '1014'
elif router_hostname == 'PE1':
    sr_index = '1015'
elif router_hostname == 'PE2':
    sr_index = '1016'
elif router_hostname == 'LE1':
    sr_index = '1017'
elif router_hostname == 'LE2':
    sr_index = '1018'
    
mpls_interfaces = mpls_int_map[router_hostname]
core_router = True if 'S' in router_hostname else False
rr_router = True if 'X' in router_hostname else False
ledge_router = True if 'L' in router_hostname else False
pedge_router = True if 'P' in router_hostname else False

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
if ledge_router:
    rr1_loopback = '172.16.250.51'
    rr2_loopback = '172.16.250.52'
if pedge_router:
    if lo_octets[-1] == '151':
        neighbor_last_octet = '152'
    elif lo_octets[-1] == '152':
        neighbor_last_octet = '151'
    else:
        raise ValueError('unacceptable loopback address {}'.format(
            local_loopback.compressed))
    neighbor_octets = lo_octets[:-1]
    neighbor_octets.append(neighbor_last_octet)
    neighbor_loopback = ipaddress.ip_address('.'.join(neighbor_octets)) 
if rr_router:
    if lo_octets[-1] == '51':
        neighbor1_last_octet = '101'        
        neighbor2_last_octet = '102'  
    elif lo_octets[-1] == '52':
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
if ledge_router:
    template = Template(frr_config_template)
    rendered = template.render(frr_version=frr_version,
                               router_hostname=router_hostname,
                               mpls_interfaces=mpls_interfaces,
                               ledge_router=ledge_router,
                               local_loopback=local_loopback.compressed,
                               rr1_loopback=rr1_loopback,
                               rr2_loopback=rr2_loopback,
                               iso_net=iso_net,
                               sr_index=sr_index,
                               local_loopback_ipv6=local_loopback_ipv6
                               )
    with open('frr_generated_config', 'w', encoding='utf-8') as config_file:
        for line in rendered.split('\n'):
            if line.strip():
                config_file.write(line+'\n')
if pedge_router:
    template = Template(frr_config_template)
    rendered = template.render(frr_version=frr_version,
                               router_hostname=router_hostname,
                               mpls_interfaces=mpls_interfaces,
                               pedge_router=pedge_router,
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
                               sr_index=sr_index,
                               local_loopback_ipv6=local_loopback_ipv6
                               )
    with open('frr_generated_config', 'w', encoding='utf-8') as config_file:
        for line in rendered.split('\n'):
            if line.strip():
                config_file.write(line+'\n')
if core_router:
    template = Template(frr_config_template)
    rendered = template.render(frr_version=frr_version,
                               router_hostname=router_hostname,
                               mpls_interfaces=mpls_interfaces,
                               core_router=core_router,
                               local_loopback=local_loopback.compressed,
                               iso_net=iso_net,
                               sr_index=sr_index,
                               local_loopback_ipv6=local_loopback_ipv6
                               )
    with open('frr_generated_config', 'w', encoding='utf-8') as config_file:
        for line in rendered.split('\n'):
            if line.strip():
                config_file.write(line+'\n')
