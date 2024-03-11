#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

class bpdu():
    def __init__(self, flags, root_bridge_id, root_path_cost, bridge_id, port_id, message_age, max_age, hello_time, forward_delay):
        self.flags = int.to_bytes(flags, 1, byteorder='big')
        self.root_bridge_id = int.to_bytes(root_bridge_id, 2, byteorder='big') + get_switch_mac()
        self.root_path_cost = int.to_bytes(root_path_cost, 4, byteorder='big')
        self.bridge_id = int.to_bytes(bridge_id, 2, byteorder='big') + get_switch_mac()
        self.port_id = int.to_bytes(port_id, 2, byteorder='big')
        self.message_age = int.to_bytes(message_age, 2, byteorder='big')
        self.max_age = int.to_bytes(max_age, 2, byteorder='big')
        self.hello_time = int.to_bytes(hello_time, 2, byteorder='big')
        self.forward_delay = int.to_bytes(forward_delay, 2, byteorder='big')

class root():
    def __init__(self, is_root):
        self.is_root = is_root

def parse_ethernet_header(data):
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec(own_bridge_id, root_obj, SW_Types, interfaces):
    while True:
        # 2. trimitere pachet BPDU la fiecare secunda
        if root_obj.is_root == True:
            for port in interfaces:
                if SW_Types[get_interface_name(port)] == 'T':
                    # crearea pachetului BPDU
                    # MAC-ul destinatie
                    dest_mac = bytes([0x01, 0x80, 0xC2, 0x00, 0x00, 0x00])

                    # headerul BPDU
                    bpdu_header = int.to_bytes(0, 4, byteorder='big')

                    # creare BPDU config
                    flags = 0
                    root_bridge_id = int(own_bridge_id)
                    root_path_cost = 0
                    bridge_id = int(own_bridge_id)
                    port_id = int(port)
                    message_age = 1
                    max_age = 20
                    hello_time = 2
                    forward_delay = 15
                    bpdu_temp = bpdu(flags, root_bridge_id, root_path_cost, bridge_id, port_id, message_age, max_age, hello_time, forward_delay)
                    bpdu_config = bpdu_temp.flags + bpdu_temp.root_bridge_id + bpdu_temp.root_path_cost + bpdu_temp.bridge_id + bpdu_temp.port_id + bpdu_temp.message_age + bpdu_temp.max_age + bpdu_temp.hello_time + bpdu_temp.forward_delay

                    # headerul LLC
                    llc_header = bytes([0x42, 0x42, 0x03])

                    # dimeniunea totala a cadrului
                    llc_length = int.to_bytes(38, 2, byteorder='big')

                    data = dest_mac + get_switch_mac() + llc_length + llc_header + bpdu_header + bpdu_config
                    send_to_link(port, data, len(data))
                    
        time.sleep(1)

def main():
    switch_id = sys.argv[1]
    MAC_Table = {}
    SW_Types = {}
    SW_States = {}
    SW_Result = {}

    filename = "switch" + switch_id + ".cfg"
    filepath = "./configs/" + filename
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    with open(filepath, 'r') as file:
        priority = file.readline()

        for line in file:
            port, type = line.split()
            SW_Types[port] = type

    # 1. initializare
    # porturile trunk se pun in starea BLOCKING
    for port in interfaces:
        if SW_Types[get_interface_name(port)] == 'T':
            SW_Result[get_interface_name(port)] = 'BLOCKING'
            SW_States[get_interface_name(port)] = 'BLOCKING'

    own_bridge_id = int(priority)
    root_bridge_id = int(priority)
    root_path_cost = 0
    root_obj = root(False)

    # portul este root
    if own_bridge_id == root_bridge_id:
        root_obj.is_root = True
        for port in interfaces:
            SW_Result[get_interface_name(port)] = 'DESIGNATED'

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    t = threading.Thread(target=send_bdpu_every_sec, args=(own_bridge_id, root_obj, SW_Types, interfaces))
    t.start()

    for i in interfaces:
        print(get_interface_name(i))

    while True:
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        MAC_Table[src_mac] = interface
    	
        # 3. primire pachet BPDU
        if dest_mac == '01:80:c2:00:00:00':
            bpdu_root_bridge_id = int.from_bytes(data[22:24], byteorder='big')
            bpdu_sender_bridge_id = int.from_bytes(data[34:36], byteorder='big')
        
            if bpdu_root_bridge_id < root_bridge_id:
                root_bridge_id = bpdu_root_bridge_id
                root_obj.is_root = False
                #  se adauga 10 la cost
                root_path_cost = int.from_bytes(data[30:34], byteorder='big') + 10
                root_port = interface

                if own_bridge_id == root_bridge_id:
                    for port in interfaces:
                        if SW_Types[get_interface_name(port)] == 'T' and port != root_port:
                            SW_States[get_interface_name(port)] = 'BLOCKING'

                if SW_States[get_interface_name(root_port)] == 'BLOCKING':
                    SW_States[get_interface_name(root_port)] = 'LISTENING'
                
                for port in interfaces:
                    if SW_Types[get_interface_name(port)] == 'T' and port != root_port:
                        # updatare si trimitere pachet BPDU
                        sender_bridge_id = own_bridge_id
                        sender_path_cost = root_path_cost

                        send_data = data[0:22] + int.to_bytes(sender_bridge_id, 2, byteorder='big') + data[24:30] + int.to_bytes(sender_path_cost, 4, byteorder='big') + data[34:] 

                        send_to_link(port, send_data, length)
            elif bpdu_root_bridge_id == root_bridge_id:
                sender_path_cost = int.from_bytes(data[30:34], byteorder='big') + 10

                for port in interfaces:
                    if port == interface and sender_path_cost < root_path_cost:
                        root_path_cost = sender_path_cost
                    elif port != interface and sender_path_cost > root_path_cost:
                        # drumul catre root e prin acest switch
                        if SW_Result[get_interface_name(port)] != 'DESIGNATED':
                            SW_States[get_interface_name(port)] = 'LISTENING'
                            SW_Result[get_interface_name(port)] = 'DESIGNATED'
            elif bpdu_sender_bridge_id == own_bridge_id:
                for port in interfaces:
                    if port != interface:
                        SW_States[get_interface_name(port)] = 'BLOCKING'
                        SW_Result[get_interface_name(port)] = 'BLOCKING'
            
            if own_bridge_id == root_bridge_id:
                for port in interfaces:
                    if SW_Types[get_interface_name(port)] == 'T':
                        SW_Result[get_interface_name(port)] = 'DESIGNATED'
                        SW_States[get_interface_name(port)] = 'LISTENING'
        else:
            # multicast si broadcast
            if int(dest_mac[1], 16) % 2 == 1:
                for port in interfaces:
                    if port != interface:
                        # cazul 1: de la trunk la trunk
                        if SW_Types[get_interface_name(port)] == 'T' and SW_Types[get_interface_name(interface)] == 'T':
                            if SW_States[get_interface_name(port)] == 'LISTENING':
                                send_to_link(port, data, length)
                        # cazul 2: de la trunk la access
                        elif SW_Types[get_interface_name(port)] != 'T' and SW_Types[get_interface_name(interface)] == 'T':
                            vlan_tci = int.from_bytes(data[14:16], byteorder='big')
                            vlan_id_curr = vlan_tci & 0x0FFF

                            if int(vlan_id_curr) == int(SW_Types[get_interface_name(port)]):
                                send_data = data[0:12] + data[16:]
                                data_length = len(send_data)
                                send_to_link(port, send_data, data_length)
                        # cazul 3: de la access la trunk
                        elif SW_Types[get_interface_name(port)] == 'T' and SW_Types[get_interface_name(interface)] != 'T':
                            send_data = data[0:12] + create_vlan_tag(int(SW_Types[get_interface_name(interface)])) + data[12:]
                            data_length = len(send_data)

                            if SW_States[get_interface_name(port)] == 'LISTENING':
                                send_to_link(port, send_data, data_length)
                        # cazul 4: de la access la access
                        elif SW_Types[get_interface_name(port)] != 'T' and SW_Types[get_interface_name(interface)] != 'T':
                            if int(SW_Types[get_interface_name(port)]) == int(SW_Types[get_interface_name(interface)]):
                                send_to_link(port, data, length)
            else: # unicast
                if dest_mac in MAC_Table:
                    # cazul 1: de la trunk la trunk
                    if SW_Types[get_interface_name(MAC_Table[dest_mac])] == 'T' and SW_Types[get_interface_name(interface)] == 'T':
                        if SW_States[get_interface_name(MAC_Table[dest_mac])] == 'LISTENING':
                            send_to_link(MAC_Table[dest_mac], data, length)
                    # cazul 2: de la trunk la access
                    elif SW_Types[get_interface_name(MAC_Table[dest_mac])] != 'T' and SW_Types[get_interface_name(interface)] == 'T':
                        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
                        vlan_id_curr = vlan_tci & 0x0FFF

                        if int(vlan_id_curr) == int(SW_Types[get_interface_name(MAC_Table[dest_mac])]):
                            send_data = data[0:12] + data[16:]
                            data_length = len(send_data)
                            send_to_link(MAC_Table[dest_mac], send_data, data_length)
                    # cazul 3: de la access la trunk
                    elif SW_Types[get_interface_name(MAC_Table[dest_mac])] == 'T' and SW_Types[get_interface_name(interface)] != 'T':
                        send_data = data[0:12] + create_vlan_tag(int(SW_Types[get_interface_name(interface)])) + data[12:]
                        data_length = len(send_data)

                        if SW_States[get_interface_name(MAC_Table[dest_mac])] == 'LISTENING':
                            send_to_link(MAC_Table[dest_mac], send_data, data_length)
                    # cazul 4: de la access la access
                    elif SW_Types[get_interface_name(MAC_Table[dest_mac])] != 'T' and SW_Types[get_interface_name(interface)] != 'T':
                        if int(SW_Types[get_interface_name(MAC_Table[dest_mac])]) == int(SW_Types[get_interface_name(interface)]):
                            send_to_link(MAC_Table[dest_mac], data, length)
                else: # unicast, nu e in tabela
                    for port in interfaces:
                        if port != interface:
                            # cazul 1: de la trunk la trunk
                            if SW_Types[get_interface_name(port)] == 'T' and SW_Types[get_interface_name(interface)] == 'T':
                                if SW_States[get_interface_name(port)] == 'LISTENING':
                                    send_to_link(port, data, length)
                            # cazul 2: de la trunk la access
                            elif SW_Types[get_interface_name(port)] != 'T' and SW_Types[get_interface_name(interface)] == 'T':
                                vlan_tci = int.from_bytes(data[14:16], byteorder='big')
                                vlan_id_curr = vlan_tci & 0x0FFF

                                if int(SW_Types[get_interface_name(port)]) == int(vlan_id_curr):
                                    send_data = data[0:12] + data[16:]
                                    data_length = len(send_data)
                                    send_to_link(port, send_data, data_length)
                            # cazul 3: de la access la trunk
                            elif SW_Types[get_interface_name(port)] == 'T' and SW_Types[get_interface_name(interface)] != 'T':
                                send_data = data[0:12] + create_vlan_tag(int(SW_Types[get_interface_name(interface)])) + data[12:]
                                data_length = len(send_data)

                                if SW_States[get_interface_name(port)] == 'LISTENING':
                                    send_to_link(port, send_data, data_length)
                            # cazul 4: de la access la access
                            elif SW_Types[get_interface_name(port)] != 'T' and SW_Types[get_interface_name(interface)] != 'T':
                                if int(SW_Types[get_interface_name(port)]) == int(SW_Types[get_interface_name(interface)]):
                                    send_to_link(port, data, length)    

if __name__ == "__main__":
    main()
