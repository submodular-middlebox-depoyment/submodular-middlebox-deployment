# MIT License
#
# Copyright (c) 2017 Matthias Rost, Alexander Elvers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__author__ = "Matthias Rost, Alexander Elvers (mrost / aelvers <AT> inet.tu-berlin.de)"

import sys

class Substrate:


    def __init__(self, name):
        self.name = name
        self.nodes = set()
        self.edges = set()
        self.edge_cost = {}
        self.out_neighbors = {}
        self.in_neighbors = {}
        self.shortest_paths_costs = None

    def add_node(self, node):
        self.nodes.add(node)
        self.out_neighbors[node] = []
        self.in_neighbors[node] = []

    def get_edge_cost(self, edge):
        return self.edge_cost[edge]

    def add_edge(self, tail, head, cost=1):
        if tail not in self.nodes or head not in self.nodes:
            print(tail)
            print(head)
            print("....")
            print(self.nodes)
            print("ERROR")
            sys.exit()
        if tail not in self.out_neighbors:
            self.out_neighbors[tail] = []
        if head not in self.in_neighbors:
            self.in_neighbors[head] = []
        self.out_neighbors[tail].append(head)
        self.in_neighbors[head].append(tail)
        self.edges.add((tail, head))
        self.edge_cost[(tail, head)] = cost

    def get_edge_capacity(self, tail, head):
        return self.edge_capacities[(tail, head)]

    def get_edge_capacity(self, edge):
        return self.edge_capacities[edge]

    def get_nodes(self):
        return self.nodes

    def get_edges(self):
        return self.edges

    def get_out_neighbors(self, node):
        return self.out_neighbors[node]

    def get_in_neighbors(self, node):
        return self.in_neighbors[node]

    def get_name(self):
        return self.name

    def get_number_of_nodes(self):
        return len(self.nodes)

    def get_number_of_edges(self):
        return len(self.edges)

    def get_shortest_paths_cost(self, node, other):
        if self.shortest_paths_costs is None:
            self.initialize_shortest_paths_costs()
        return self.shortest_paths_costs[node][other]

    def get_shortest_paths_cost_dict(self):
        if self.shortest_paths_costs is None:
            self.initialize_shortest_paths_costs()
        return self.shortest_paths_costs


    def initialize_shortest_paths_costs(self):
        self.shortest_paths_costs = {}
        for u in self.nodes:
            self.shortest_paths_costs[u] = {}
            for v in self.nodes:
                if u is v:
                    self.shortest_paths_costs[u][v] = 0
                else:
                    self.shortest_paths_costs[u][v] = None


        for (u,v) in self.edges:
            self.shortest_paths_costs[u][v] = self.edge_cost[(u,v)]

        for k in self.nodes:
            for u in self.nodes:
                for v in self.nodes:
                    if self.shortest_paths_costs[u][k] is not None and self.shortest_paths_costs[k][v] is not None:
                        cost_via_k = self.shortest_paths_costs[u][k] + self.shortest_paths_costs[k][v]
                        if self.shortest_paths_costs[u][v] is None or cost_via_k < self.shortest_paths_costs[u][v]:
                            self.shortest_paths_costs[u][v] = cost_via_k


    def check_connectivity(self):
        if self.shortest_paths_costs is None:
            self.initialize_shortest_paths_costs()
        for u in self.nodes:
            for v in self.nodes:
                if self.shortest_paths_costs[u][v] is None:
                    return False

        return True


    def print_it(self, including_shortest_path_costs=True):
        print("Nodes:")
        print(self.nodes)
        print("\n\n")
        print("Edges:")
        print(self.edges)
        print(self.edge_cost)
        if including_shortest_path_costs:
            if self.shortest_paths_costs is None:
                self.initialize_shortest_paths_costs()
            print("Distances:")
            for u in self.nodes:
                for v in self.nodes:
                    print("{} to {}: {}".format(u,v,self.shortest_paths_costs[u][v]))
