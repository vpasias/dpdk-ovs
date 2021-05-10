# -*- mode: ruby -*-
# vi: set ft=ruby :

# Open vSwitch 	DPDK
# 2.6.x         16.07.2
# 2.7.x         16.11.6
# 2.8.x         17.05.2
# 2.9.x         17.11.2
# 2.14.x        19.11.2
# 2.15.x        20.11.0

$script1 = <<SCRIPT
set -e -x -u
# Configure hugepages
# You can later check if this change was successful with `cat /proc/meminfo`
# Hugepages setup should be done as early as possible after boot
echo 'vm.nr_hugepages=1024' | sudo tee /etc/sysctl.d/hugepages.conf
sudo mount -t hugetlbfs none /dev/hugepages
sudo sysctl -w vm.nr_hugepages=1024

sudo cp /tmp/ovs-vswitchd.service /etc/systemd/system/ovs-vswitchd.service
sudo cp /tmp/ovsdb-server.service /etc/systemd/system/ovsdb-server.service

# Name of network interface provisioned for DPDK to bind
export NET_IF1_NAME=enp0s8
export NET_IF2_NAME=enp0s9
export NET_IF3_NAME=enp0s10
export NET_IF4_NAME=enp0s11

sudo apt-get -qq update
sudo apt-get -y -qq install vim git clang doxygen hugepages build-essential libnuma-dev libpcap-dev linux-headers-`uname -r` dh-autoreconf libssl-dev libcap-ng-dev openssl python python-pip htop
sudo apt-get -y -qq install apt-transport-https ca-certificates curl gnupg lsb-release
sudo pip install six

#### Install Golang
wget --quiet https://storage.googleapis.com/golang/go1.9.1.linux-amd64.tar.gz
sudo tar -zxf go1.9.1.linux-amd64.tar.gz -C /usr/local/
echo 'export GOROOT=/usr/local/go' >> /home/vagrant/.bashrc
echo 'export GOPATH=$HOME/go' >> /home/vagrant/.bashrc
echo 'export PATH=$PATH:$GOROOT/bin:$GOPATH/bin' >> /home/vagrant/.bashrc
source /home/vagrant/.bashrc
mkdir -p /home/vagrant/go/src
rm -rf /home/vagrant/go1.9.1.linux-amd64.tar.gz

#### Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get -qq update
sudo apt-get -qq install -y docker-ce docker-ce-cli containerd.io

#### Download DPDK, Open vSwitch and pktgen source
wget --quiet https://fast.dpdk.org/rel/dpdk-19.11.2.tar.xz
sudo tar xf dpdk-19.11.2.tar.xz -C /usr/src/

wget --quiet http://openvswitch.org/releases/openvswitch-2.14.2.tar.gz
sudo tar -zxf openvswitch-2.14.2.tar.gz -C /usr/src/

wget --quiet http://www.dpdk.org/browse/apps/pktgen-dpdk/snapshot/pktgen-3.4.9.tar.gz
sudo tar -zxf pktgen-3.4.9.tar.gz -C /usr/src/

#### Install DPDK
echo 'export DPDK_DIR=/usr/src/dpdk-stable-19.11.2' | sudo tee -a /root/.bashrc
echo 'export LD_LIBRARY_PATH=$DPDK_DIR/x86_64-native-linuxapp-gcc/lib' | sudo tee -a /root/.bashrc
echo 'export DPDK_TARGET=x86_64-native-linuxapp-gcc' | sudo tee -a /root/.bashrc
echo 'export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET' | sudo tee -a /root/.bashrc
export DPDK_DIR=/usr/src/dpdk-stable-19.11.2
export LD_LIBRARY_PATH=$DPDK_DIR/x86_64-native-linuxapp-gcc/lib
export DPDK_TARGET=x86_64-native-linuxapp-gcc
export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET

cd $DPDK_DIR
# Build and install the DPDK library
sudo make install T=$DPDK_TARGET DESTDIR=install
# (Optional) Export the DPDK shared library location
sudo sed -i 's/CONFIG_RTE_BUILD_SHARED_LIB=n/CONFIG_RTE_BUILD_SHARED_LIB=y/g' ${DPDK_DIR}/config/common_base

# Install kernel modules
sudo modprobe uio
sudo insmod ${DPDK_DIR}/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko

# Make uio and igb_uio installations persist across reboots
sudo ln -sf ${DPDK_DIR}/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko /lib/modules/`uname -r`
sudo depmod -a
echo "uio" | sudo tee -a /etc/modules
echo "igb_uio" | sudo tee -a /etc/modules

# Bind secondary network adapter
# Note that this NIC setup does not persist across reboots
sudo ifconfig ${NET_IF1_NAME} down
sudo ifconfig ${NET_IF2_NAME} down
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF1_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF2_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --status

#### Install Open vSwitch
export OVS_DIR=/usr/src/openvswitch-2.14.2
cd $OVS_DIR
#./boot.sh
CFLAGS='-march=native' sudo ./configure --prefix=/usr --localstatedir=/var --sysconfdir=/etc --with-dpdk=$DPDK_BUILD
sudo make && sudo make install
sudo mkdir -p /usr/local/etc/openvswitch
sudo mkdir -p /usr/local/var/run/openvswitch
sudo mkdir -p /usr/local/var/log/openvswitch
sudo ovsdb-tool create /usr/local/etc/openvswitch/conf.db vswitchd/vswitch.ovsschema

echo 'export PATH=$PATH:/usr/local/share/openvswitch/scripts' | sudo tee -a /root/.bashrc

sudo systemctl enable ovsdb-server
sudo systemctl start ovsdb-server

sudo systemctl enable ovs-vswitchd
sudo systemctl start ovs-vswitchd

#### Cleanup
rm -rf /home/vagrant/openvswitch-2.14.2.tar.gz /home/vagrant/dpdk-19.11.2.tar.xz /home/vagrant/go1.9.1.linux-amd64.tar.gz /home/vagrant/pktgen-3.4.9.tar.gz

sudo systemctl start ovsdb-server
sudo systemctl start ovs-vswitchd

sudo systemctl status ovsdb-server
sudo systemctl status ovs-vswitchd
sudo lshw -class network -businfo

sudo ovs-vsctl --no-wait init
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=true
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-socket-mem="1024"
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask=0x2
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:max-idle=30000

# userspace datapath with dpdk
sudo ovs-vsctl add-br br1 -- set bridge br1 datapath_type=netdev
sudo ovs-vsctl add-port br1 dpdk0 -- set Interface dpdk0 type=dpdk options:dpdk-devargs=0000:00:08.0
sudo ovs-vsctl add-br br2 -- set bridge br2 datapath_type=netdev
sudo ovs-vsctl add-port br2 dpdk1 -- set Interface dpdk1 type=dpdk options:dpdk-devargs=0000:00:09.0 

# kernel datapath
sudo ovs-vsctl add-br br0 -- set bridge br0 datapath_type=system
sudo ovs-vsctl show

sudo ip addr add 172.16.150.90/24 dev br1
sudo ip link set br1 up
sudo ip addr add 172.16.250.90/24 dev br2
sudo ip link set br2 up

# End of script1
SCRIPT

$script2 = <<SCRIPT
set -e -x -u
# Configure hugepages
# You can later check if this change was successful with `cat /proc/meminfo`
# Hugepages setup should be done as early as possible after boot
echo 'vm.nr_hugepages=1024' | sudo tee /etc/sysctl.d/hugepages.conf
sudo mount -t hugetlbfs none /dev/hugepages
sudo sysctl -w vm.nr_hugepages=1024

sudo cp /tmp/ovs-vswitchd.service /etc/systemd/system/ovs-vswitchd.service
sudo cp /tmp/ovsdb-server.service /etc/systemd/system/ovsdb-server.service

# Name of network interface provisioned for DPDK to bind
export NET_IF1_NAME=enp0s8
export NET_IF2_NAME=enp0s9
export NET_IF3_NAME=enp0s10
export NET_IF4_NAME=enp0s11

sudo apt-get -qq update
sudo apt-get -y -qq install vim git clang doxygen hugepages build-essential libnuma-dev libpcap-dev linux-headers-`uname -r` dh-autoreconf libssl-dev libcap-ng-dev openssl python python-pip htop
sudo apt-get -y -qq install apt-transport-https ca-certificates curl gnupg lsb-release
sudo pip install six

#### Install Golang
wget --quiet https://storage.googleapis.com/golang/go1.9.1.linux-amd64.tar.gz
sudo tar -zxf go1.9.1.linux-amd64.tar.gz -C /usr/local/
echo 'export GOROOT=/usr/local/go' >> /home/vagrant/.bashrc
echo 'export GOPATH=$HOME/go' >> /home/vagrant/.bashrc
echo 'export PATH=$PATH:$GOROOT/bin:$GOPATH/bin' >> /home/vagrant/.bashrc
source /home/vagrant/.bashrc
mkdir -p /home/vagrant/go/src
rm -rf /home/vagrant/go1.9.1.linux-amd64.tar.gz

#### Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get -qq update
sudo apt-get -qq install -y docker-ce docker-ce-cli containerd.io

#### Download DPDK, Open vSwitch and pktgen source
wget --quiet https://fast.dpdk.org/rel/dpdk-19.11.2.tar.xz
sudo tar xf dpdk-19.11.2.tar.xz -C /usr/src/

wget --quiet http://openvswitch.org/releases/openvswitch-2.14.2.tar.gz
sudo tar -zxf openvswitch-2.14.2.tar.gz -C /usr/src/

wget --quiet http://www.dpdk.org/browse/apps/pktgen-dpdk/snapshot/pktgen-3.4.9.tar.gz
sudo tar -zxf pktgen-3.4.9.tar.gz -C /usr/src/

#### Install DPDK
echo 'export DPDK_DIR=/usr/src/dpdk-stable-19.11.2' | sudo tee -a /root/.bashrc
echo 'export LD_LIBRARY_PATH=$DPDK_DIR/x86_64-native-linuxapp-gcc/lib' | sudo tee -a /root/.bashrc
echo 'export DPDK_TARGET=x86_64-native-linuxapp-gcc' | sudo tee -a /root/.bashrc
echo 'export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET' | sudo tee -a /root/.bashrc
export DPDK_DIR=/usr/src/dpdk-stable-19.11.2
export LD_LIBRARY_PATH=$DPDK_DIR/x86_64-native-linuxapp-gcc/lib
export DPDK_TARGET=x86_64-native-linuxapp-gcc
export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET

cd $DPDK_DIR
# Build and install the DPDK library
sudo make install T=$DPDK_TARGET DESTDIR=install
# (Optional) Export the DPDK shared library location
sudo sed -i 's/CONFIG_RTE_BUILD_SHARED_LIB=n/CONFIG_RTE_BUILD_SHARED_LIB=y/g' ${DPDK_DIR}/config/common_base

# Install kernel modules
sudo modprobe uio
sudo insmod ${DPDK_DIR}/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko

# Make uio and igb_uio installations persist across reboots
sudo ln -sf ${DPDK_DIR}/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko /lib/modules/`uname -r`
sudo depmod -a
echo "uio" | sudo tee -a /etc/modules
echo "igb_uio" | sudo tee -a /etc/modules

# Bind secondary network adapter
# Note that this NIC setup does not persist across reboots
sudo ifconfig ${NET_IF1_NAME} down
sudo ifconfig ${NET_IF2_NAME} down
sudo ifconfig ${NET_IF3_NAME} down
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF1_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF2_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF3_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --status

#### Install Open vSwitch
export OVS_DIR=/usr/src/openvswitch-2.14.2
cd $OVS_DIR
#./boot.sh
CFLAGS='-march=native' sudo ./configure --prefix=/usr --localstatedir=/var --sysconfdir=/etc --with-dpdk=$DPDK_BUILD
sudo make && sudo make install
sudo mkdir -p /usr/local/etc/openvswitch
sudo mkdir -p /usr/local/var/run/openvswitch
sudo mkdir -p /usr/local/var/log/openvswitch
sudo ovsdb-tool create /usr/local/etc/openvswitch/conf.db vswitchd/vswitch.ovsschema

echo 'export PATH=$PATH:/usr/local/share/openvswitch/scripts' | sudo tee -a /root/.bashrc

sudo systemctl enable ovsdb-server
sudo systemctl start ovsdb-server

sudo systemctl enable ovs-vswitchd
sudo systemctl start ovs-vswitchd

#### Cleanup
rm -rf /home/vagrant/openvswitch-2.14.2.tar.gz /home/vagrant/dpdk-19.11.2.tar.xz /home/vagrant/go1.9.1.linux-amd64.tar.gz /home/vagrant/pktgen-3.4.9.tar.gz

sudo systemctl start ovsdb-server
sudo systemctl start ovs-vswitchd

sudo systemctl status ovsdb-server
sudo systemctl status ovs-vswitchd
sudo lshw -class network -businfo

sudo ovs-vsctl --no-wait init
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=true
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-socket-mem="1024"
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask=0x2
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:max-idle=30000

# userspace datapath with dpdk
sudo ovs-vsctl add-br br1 -- set bridge br1 datapath_type=netdev
sudo ovs-vsctl add-port br1 dpdk0 -- set Interface dpdk0 type=dpdk options:dpdk-devargs=0000:00:08.0
sudo ovs-vsctl add-br br2 -- set bridge br2 datapath_type=netdev
sudo ovs-vsctl add-port br2 dpdk1 -- set Interface dpdk1 type=dpdk options:dpdk-devargs=0000:00:09.0
sudo ovs-vsctl add-br br3 -- set bridge br3 datapath_type=netdev
sudo ovs-vsctl add-port br3 dpdk2 -- set Interface dpdk2 type=dpdk options:dpdk-devargs=0000:00:0a.0 

# kernel datapath
sudo ovs-vsctl add-br br0 -- set bridge br0 datapath_type=system
sudo ovs-vsctl show

sudo ip addr add 172.16.111.100/24 dev br1
sudo ip link set br1 up
sudo ip addr add 172.16.112.100/24 dev br2
sudo ip link set br2 up
sudo ip addr add 172.16.150.100/24 dev br3
sudo ip link set br3 up

# End of script2
SCRIPT

$script3 = <<SCRIPT
set -e -x -u
# Configure hugepages
# You can later check if this change was successful with `cat /proc/meminfo`
# Hugepages setup should be done as early as possible after boot
echo 'vm.nr_hugepages=1024' | sudo tee /etc/sysctl.d/hugepages.conf
sudo mount -t hugetlbfs none /dev/hugepages
sudo sysctl -w vm.nr_hugepages=1024

sudo cp /tmp/ovs-vswitchd.service /etc/systemd/system/ovs-vswitchd.service
sudo cp /tmp/ovsdb-server.service /etc/systemd/system/ovsdb-server.service

# Name of network interface provisioned for DPDK to bind
export NET_IF1_NAME=enp0s8
export NET_IF2_NAME=enp0s9
export NET_IF3_NAME=enp0s10
export NET_IF4_NAME=enp0s11

sudo apt-get -qq update
sudo apt-get -y -qq install vim git clang doxygen hugepages build-essential libnuma-dev libpcap-dev linux-headers-`uname -r` dh-autoreconf libssl-dev libcap-ng-dev openssl python python-pip htop
sudo apt-get -y -qq install apt-transport-https ca-certificates curl gnupg lsb-release
sudo pip install six

#### Install Golang
wget --quiet https://storage.googleapis.com/golang/go1.9.1.linux-amd64.tar.gz
sudo tar -zxf go1.9.1.linux-amd64.tar.gz -C /usr/local/
echo 'export GOROOT=/usr/local/go' >> /home/vagrant/.bashrc
echo 'export GOPATH=$HOME/go' >> /home/vagrant/.bashrc
echo 'export PATH=$PATH:$GOROOT/bin:$GOPATH/bin' >> /home/vagrant/.bashrc
source /home/vagrant/.bashrc
mkdir -p /home/vagrant/go/src
rm -rf /home/vagrant/go1.9.1.linux-amd64.tar.gz

#### Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get -qq update
sudo apt-get -qq install -y docker-ce docker-ce-cli containerd.io

#### Download DPDK, Open vSwitch and pktgen source
wget --quiet https://fast.dpdk.org/rel/dpdk-19.11.2.tar.xz
sudo tar xf dpdk-19.11.2.tar.xz -C /usr/src/

wget --quiet http://openvswitch.org/releases/openvswitch-2.14.2.tar.gz
sudo tar -zxf openvswitch-2.14.2.tar.gz -C /usr/src/

wget --quiet http://www.dpdk.org/browse/apps/pktgen-dpdk/snapshot/pktgen-3.4.9.tar.gz
sudo tar -zxf pktgen-3.4.9.tar.gz -C /usr/src/

#### Install DPDK
echo 'export DPDK_DIR=/usr/src/dpdk-stable-19.11.2' | sudo tee -a /root/.bashrc
echo 'export LD_LIBRARY_PATH=$DPDK_DIR/x86_64-native-linuxapp-gcc/lib' | sudo tee -a /root/.bashrc
echo 'export DPDK_TARGET=x86_64-native-linuxapp-gcc' | sudo tee -a /root/.bashrc
echo 'export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET' | sudo tee -a /root/.bashrc
export DPDK_DIR=/usr/src/dpdk-stable-19.11.2
export LD_LIBRARY_PATH=$DPDK_DIR/x86_64-native-linuxapp-gcc/lib
export DPDK_TARGET=x86_64-native-linuxapp-gcc
export DPDK_BUILD=$DPDK_DIR/$DPDK_TARGET

cd $DPDK_DIR
# Build and install the DPDK library
sudo make install T=$DPDK_TARGET DESTDIR=install
# (Optional) Export the DPDK shared library location
sudo sed -i 's/CONFIG_RTE_BUILD_SHARED_LIB=n/CONFIG_RTE_BUILD_SHARED_LIB=y/g' ${DPDK_DIR}/config/common_base

# Install kernel modules
sudo modprobe uio
sudo insmod ${DPDK_DIR}/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko

# Make uio and igb_uio installations persist across reboots
sudo ln -sf ${DPDK_DIR}/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko /lib/modules/`uname -r`
sudo depmod -a
echo "uio" | sudo tee -a /etc/modules
echo "igb_uio" | sudo tee -a /etc/modules

# Bind secondary network adapter
# Note that this NIC setup does not persist across reboots
sudo ifconfig ${NET_IF1_NAME} down
sudo ifconfig ${NET_IF2_NAME} down
sudo ifconfig ${NET_IF3_NAME} down
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF1_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF2_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --bind=igb_uio ${NET_IF3_NAME}
sudo ${DPDK_DIR}/usertools/dpdk-devbind.py --status

#### Install Open vSwitch
export OVS_DIR=/usr/src/openvswitch-2.14.2
cd $OVS_DIR
#./boot.sh
CFLAGS='-march=native' sudo ./configure --prefix=/usr --localstatedir=/var --sysconfdir=/etc --with-dpdk=$DPDK_BUILD
sudo make && sudo make install
sudo mkdir -p /usr/local/etc/openvswitch
sudo mkdir -p /usr/local/var/run/openvswitch
sudo mkdir -p /usr/local/var/log/openvswitch
sudo ovsdb-tool create /usr/local/etc/openvswitch/conf.db vswitchd/vswitch.ovsschema

echo 'export PATH=$PATH:/usr/local/share/openvswitch/scripts' | sudo tee -a /root/.bashrc

sudo systemctl enable ovsdb-server
sudo systemctl start ovsdb-server

sudo systemctl enable ovs-vswitchd
sudo systemctl start ovs-vswitchd

#### Cleanup
rm -rf /home/vagrant/openvswitch-2.14.2.tar.gz /home/vagrant/dpdk-19.11.2.tar.xz /home/vagrant/go1.9.1.linux-amd64.tar.gz /home/vagrant/pktgen-3.4.9.tar.gz

sudo systemctl start ovsdb-server
sudo systemctl start ovs-vswitchd

sudo systemctl status ovsdb-server
sudo systemctl status ovs-vswitchd
sudo lshw -class network -businfo

sudo ovs-vsctl --no-wait init
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-init=true
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:dpdk-socket-mem="1024"
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask=0x2
sudo ovs-vsctl --no-wait set Open_vSwitch . other_config:max-idle=30000

# userspace datapath with dpdk
sudo ovs-vsctl add-br br1 -- set bridge br1 datapath_type=netdev
sudo ovs-vsctl add-port br1 dpdk0 -- set Interface dpdk0 type=dpdk options:dpdk-devargs=0000:00:08.0
sudo ovs-vsctl add-br br2 -- set bridge br2 datapath_type=netdev
sudo ovs-vsctl add-port br2 dpdk1 -- set Interface dpdk1 type=dpdk options:dpdk-devargs=0000:00:09.0
sudo ovs-vsctl add-br br3 -- set bridge br3 datapath_type=netdev
sudo ovs-vsctl add-port br3 dpdk2 -- set Interface dpdk2 type=dpdk options:dpdk-devargs=0000:00:0a.0 

# kernel datapath
sudo ovs-vsctl add-br br0 -- set bridge br0 datapath_type=system
sudo ovs-vsctl show

sudo ip addr add 172.16.211.100/24 dev br1
sudo ip link set br1 up
sudo ip addr add 172.16.212.100/24 dev br2
sudo ip link set br2 up
sudo ip addr add 172.16.250.100/24 dev br3
sudo ip link set br3 up

# End of script3
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.define "p1" do |p1|
      p1.vm.box = "ubuntu/bionic64"
      p1.vm.hostname = "P1"
      p1.vm.provision "shell", path: "gen_provisioning-unf"
      p1.vm.provision :reload
      p1.vm.provision "file", source: "systemctl/ovs-vswitchd.service", destination: "/tmp/ovs-vswitchd.service"
      p1.vm.provision "file", source: "systemctl/ovsdb-server.service", destination: "/tmp/ovsdb-server.service"
      p1.vm.provision "shell", privileged: false, inline: $script1
      p1.vm.network "private_network", ip: "172.16.150.90", virtualbox_intnet: "pe1p1"
      p1.vm.network "private_network", ip: "172.16.250.90", virtualbox_intnet: "pe2p1"
      # Create a private network, which allows host-only access to the machine using a specific IP.
      # This option is needed otherwise the Intel DPDK takes over the entire adapter.
      p1.vm.provider :virtualbox do |vbox|
            vbox.name = "P1"
            vbox.customize ["modifyvm", :id, "--cpus", 2]
            vbox.customize ["modifyvm", :id, "--memory", 8192]
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
            vbox.customize ['modifyvm', :id, '--nictype3', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc3', 'allow-all']
            # Configure VirtualBox to enable passthrough of SSE 4.1 and SSE 4.2
            # instructions, according to this:
            # https://www.virtualbox.org/manual/ch09.html#sse412passthrough
            # This step is fundamental otherwise DPDK won't build.
            # It is possible to verify in the guest OS that these changes took effect
            # by running `cat /proc/cpuinfo` and checking that `sse4_1` and `sse4_2`
            # are listed among the CPU flags
            vbox.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
            vbox.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
      end # end provider
      p1.vm.provision "file", source: "gen_frr_config.py", destination: "gen_frr_config.py"
      p1.vm.provision "shell", path: "l3vpn_provisioning"
  end
  config.vm.define "pe1" do |pe1|
      pe1.vm.box = "ubuntu/bionic64"
      pe1.vm.hostname = "PE1"
      pe1.vm.provision "shell", path: "gen_provisioning-unf"
      pe1.vm.provision :reload
      pe1.vm.provision "file", source: "systemctl/ovs-vswitchd.service", destination: "/tmp/ovs-vswitchd.service"
      pe1.vm.provision "file", source: "systemctl/ovsdb-server.service", destination: "/tmp/ovsdb-server.service"
      pe1.vm.provision "shell", privileged: false, inline: $script2
      pe1.vm.network "private_network", ip: "172.16.111.100", virtualbox_intnet: "pe1ce1"
      pe1.vm.network "private_network", ip: "172.16.112.100", virtualbox_intnet: "pe1ce2"
      pe1.vm.network "private_network", ip: "172.16.150.100", virtualbox_intnet: "pe1p1"
      pe1.vm.provider :virtualbox do |vbox|
            vbox.name = "PE1"
            vbox.customize ["modifyvm", :id, "--cpus", 2]
            vbox.customize ["modifyvm", :id, "--memory", 8192]
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
            vbox.customize ['modifyvm', :id, '--nictype3', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc3', 'allow-all']
            vbox.customize ['modifyvm', :id, '--nictype4', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc4', 'allow-all']
            vbox.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
            vbox.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
      end
      pe1.vm.provision "file", source: "gen_frr_config.py", destination: "gen_frr_config.py"
      pe1.vm.provision "shell", path: "l3vpn_provisioning"
  end
  config.vm.define "pe2" do |pe2|
      pe2.vm.box = "ubuntu/bionic64"
      pe2.vm.hostname = "PE2"
      pe2.vm.provision "shell", path: "gen_provisioning-unf"
      pe2.vm.provision :reload
      pe2.vm.provision "file", source: "systemctl/ovs-vswitchd.service", destination: "/tmp/ovs-vswitchd.service"
      pe2.vm.provision "file", source: "systemctl/ovsdb-server.service", destination: "/tmp/ovsdb-server.service"
      pe2.vm.provision "shell", privileged: false, inline: $script3
      pe2.vm.network "private_network", ip: "172.16.211.100", virtualbox_intnet: "pe2ce3"
      pe2.vm.network "private_network", ip: "172.16.212.100", virtualbox_intnet: "pe2ce4"
      pe2.vm.network "private_network", ip: "172.16.250.100", virtualbox_intnet: "pe2p1"
      pe2.vm.provider :virtualbox do |vbox|
            vbox.name = "PE2"
            vbox.customize ["modifyvm", :id, "--cpus", 2]
            vbox.customize ["modifyvm", :id, "--memory", 8192]
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
            vbox.customize ['modifyvm', :id, '--nictype3', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc3', 'allow-all']
            vbox.customize ['modifyvm', :id, '--nictype4', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc4', 'allow-all']
            vbox.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
            vbox.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
      end
      pe2.vm.provision "file", source: "gen_frr_config.py", destination: "gen_frr_config.py"
      pe2.vm.provision "shell", path: "l3vpn_provisioning"
  end
  config.vm.define "ce1" do |ce1|
      ce1.vm.box = "generic/ubuntu2004"
      ce1.vm.hostname = "CE1"
      ce1.vm.network "private_network", ip: "172.16.111.10", virtualbox_intnet: "pe1ce1"
      ce1.vm.provider "virtualbox" do |vbox|
            vbox.name = "CE1"
            vbox.memory = 16384
            vbox.cpus = 4
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
      end
      ce1.vm.provision "shell", path: "l3vpn_provisioning"
  end
  config.vm.define "ce2" do |ce2|
      ce2.vm.box = "generic/ubuntu2004"
      ce2.vm.hostname = "CE2"
      ce2.vm.network "private_network", ip: "172.16.112.10", virtualbox_intnet: "pe1ce2"
      ce2.vm.provider "virtualbox" do |vbox|
            vbox.name = "CE2"
            vbox.memory = 16384
            vbox.cpus = 4
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
      end
      ce2.vm.provision "shell", path: "l3vpn_provisioning"
  end
  config.vm.define "ce3" do |ce3|
      ce3.vm.box = "generic/ubuntu2004"
      ce3.vm.hostname = "CE3"
      ce3.vm.network "private_network", ip: "172.16.211.10", virtualbox_intnet: "pe2ce3"
      ce3.vm.provider "virtualbox" do |vbox|
            vbox.name = "CE3"
            vbox.memory = 16384
            vbox.cpus = 4
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
      end
      ce3.vm.provision "shell", path: "l3vpn_provisioning"
  end
  config.vm.define "ce4" do |ce4|
      ce4.vm.box = "generic/ubuntu2004"
      ce4.vm.hostname = "CE4"
      ce4.vm.network "private_network", ip: "172.16.212.10", virtualbox_intnet: "pe2ce4"
      ce4.vm.provider "virtualbox" do |vbox|
            vbox.name = "CE4"
            vbox.memory = 16384
            vbox.cpus = 4
            vbox.customize ["modifyvm", :id, "--chipset", "ich9"]
            vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
            vbox.customize ['modifyvm', :id, '--nictype2', '82545EM']
            vbox.customize ['modifyvm', :id, '--nicpromisc2', 'allow-all']
      end
      ce4.vm.provision "shell", path: "l3vpn_provisioning"
  end
end
