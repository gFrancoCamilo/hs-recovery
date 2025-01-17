import subprocess
import os
import sys
import json
import math
import argparse

import numpy as np

# This macro (BASE_PORT) has to be set to the same value as the one in the
# ./benchmark/local.py
BASE_PORT = 10000

class Scenario:

    def __init__ (self, num_chains, num_honest, num_nodes, allow_communications, network_delay, verbose):
        #self.faults = faults
        self.allow_communications = allow_communications
        self.network_delay = network_delay
        self.num_nodes = num_nodes
        self.num_honest = num_honest
        self.num_chains = num_chains
        self.verbose = verbose


    def  _get_number_honest_parties (self):
        return self.num_honest
    
    def _get_number_shadows (self):
        return math.ceil((self.num_nodes - self.num_honest)/self.num_chains)
    
    def _get_total_number_nodes (self):
        return self.num_nodes

    def _get_honest_parties(self):
        return [i for i in range(self._get_number_honest_parties())]
    
    def _get_cliques (self):
        """
        Create the cliques based on the configuration given to us by the user.
        Basically, we split the twins in the cliques (i.e. number of chains)
        and we add the honest nodes to each chain later
        """
        nodes = [i for i in range(self._get_total_number_nodes())]
        nodes_minus_honest = nodes[self._get_number_honest_parties():]

        cliques = np.array_split(np.array(nodes_minus_honest), self.num_chains)
        cliques = [clique.tolist() for clique in cliques]

        honest_parties = self._get_honest_parties()

        # Distribute the honest nodes to every clique
        for i in range(len(honest_parties)):
            cliques[i % self.num_chains].append(i)
        return cliques

    def _create_dns_file (self):
        """
        Create a DNS configuration file mapping node IDs to their respective ports.
        This initial configuration is for local use, given that we don't know which
        IPs AWS will use unitl we run it.
        """
        dns = {}
        for i in range(self._get_total_number_nodes()):
            dns[i] = "127.0.0.1:" + str(BASE_PORT + i)
        with open("./benchmark/.dns.json","w") as f:
            json.dump(dns, f, indent=4, sort_keys=True)

    
    def _print(self):
        """
        Prints somee of the cofigurations. Mostly for debugging
        """
        print('------------------------------------------------')
        print('                     Scenario                   ')
        print('------------------------------------------------')
        print('Total number of nodes: {}'.format(self._get_total_number_nodes()))
        print('Cliques: {}'.format(self._get_cliques()))
        print('Number of shadows: {}'.format(self._get_number_shadows()))
        print('------------------------------------------------')
    
    def _create_network_params_file(self, path='./benchmark/.network_params.json'):
        """
        Create the network parameters file, which is used by the Rust code to
        configure the network. Among other things, this function mainly defines
        the firewall of each node based based  on the parameters of the scenario
        and writes them into a file (.network_params.json)
        """
        firewalls = {}
        cliques = self._get_cliques()
        num_stages = len(cliques) + 1
        honest_nodes = self._get_honest_parties()
        

        for node in range(self.num_nodes):
            # Getting the clique in which the node is part of
            firewalls[f"node_{node}"] = {}
            node_clique = [clique for clique in cliques if node in clique]
            node_clique = node_clique[0]
            
            # Getting the rest of the cliques (cliques in which the node is not a participant)
            rest_cliques = []
            rest_cliques.append([clique for clique in cliques if node not in clique])
            rest_cliques = rest_cliques[0]
            
            for stage in range(num_stages):
                blocked = []
                # First stage: just block everyone not in the clique
                if stage == 0:
                    blocked = [
                        f"127.0.0.1:{BASE_PORT+n}"
                        for n in range(self.num_nodes)
                        if n not in node_clique
                    ]
                elif stage < num_stages - 1:
                # Intermediary stage has a different procedure for honest nodes and twins
                    if node < self.num_honest:
                    # Begin procedure for honest node
                       clique_to_allow = rest_cliques[stage - 1]
                       honest_nodes_from_cliques_to_allow = [honest_node for honest_node in clique_to_allow if honest_node < self.num_honest]
                       blocked = [
                           f"127.0.0.1:{BASE_PORT+n}"
                           for n in range(self.num_nodes)
                           if n != node and n not in node_clique and n not in honest_nodes_from_cliques_to_allow
                        ]
                    else:
                    # Begin procedure for malicious nodes
                    # In this case, we just add whoever is not in the clique
                        blocked = [
                            f"127.0.0.1:{BASE_PORT+n}"
                            for n in range(self.num_nodes)
                            if n not in node_clique
                        ]
                else:
                   blocked = [
                       f"127.0.0.1:{BASE_PORT+n}"
                       for n in range(self.num_nodes)
                       if n not in node_clique and n > self.num_honest - 1
                    ]
                firewalls[f"node_{node}"][f"{stage}"] = blocked 


        if self.verbose:
            for node in firewalls:
                print('{}: {}\n-----------------------------------------------------'.format(node, firewalls[node]))

        # Setting othr params for simulation
        firewalls['num_of_twins'] = self._get_number_shadows() * (self.num_chains - 1)
        firewalls['allow_communications_at_round'] = self.allow_communications
        firewalls['network_delay'] = self.network_delay

        # Writing to file
        with open(path, 'w') as f:
            json.dump(firewalls, f, indent=4, sort_keys=True)
        
        # This stores some extar info about the scenario in case another file needs it
        env_info = {}
        env_info['num_chains'] = self.num_chains
        env_info['num_honest'] = self.num_honest
        env_info['num_nodes'] = self.num_nodes
        nodes = int((self.num_nodes - self.num_honest)/self.num_chains + self.num_honest)
        env_info['nodes'] = nodes
        with open('./benchmark/.env-info.json', 'w') as f:
            json.dump(env_info, f, indent = 4, sort_keys = True)
            

        return firewalls

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='./setup-env.py')
    parser.add_argument('-v', '--verbose', action = 'store_true', help = 'verbose mode')
    parser.add_argument('-n', '--nodes', type = int, help = 'total number of nodes', default = 15)
    parser.add_argument('-c', '--cliques', type = int, help = 'number of cliques (chains)', default = 3)
    parser.add_argument('-d', '--delay', type = int, help = 'network delay. Only use it if running locally.\
            This sets a random network delay in the range of the argument passed to every message sent to \
            simulate a real network behavior. The unit is ms.', default = 1)
    parser.add_argument('-l', '--honest', type = int, help = 'total number of honest nodes', default = 3)
    parser.add_argument('-a', '--allow_communication', type = int, help = 'number of rouds until honest nodes reestablish\
            communication. If the number of recoveries is bigger than 1, this recoveries will take place in rounds which\
            are multiples of this number. As a example, if allow_communication is set to 50 and there are 2 recoveries, they will\
            take place at roud 50 and 100.', default = 50)

    args = parser.parse_args()

    print('Setting up the environment...')
    scenario = Scenario(args.cliques, args.honest, args.nodes, args.allow_communication, args.delay, args.verbose)
    if args.verbose:
        scenario._print()
    scenario._create_network_params_file()
    scenario._create_dns_file()
