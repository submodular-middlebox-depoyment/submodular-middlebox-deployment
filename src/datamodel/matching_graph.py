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

from util import util as util_pkg

def get_copy_stateful_matching_graph(other):
    new_mg = StatefulMatchingGraph(other.scenario)


class MatchingGraph:

    def __init__(self, scenario, orig=None):

        self.scenario = scenario
        #util_pkg.prettyPrint(scenario)

        self.middleboxes = self.scenario.middleboxes.keys()

        #print "\n\n INIT \n {} \n\n".format(self.middleboxes)
        self.communication_pairs = range(len(self.scenario.requests))


        if orig is None:
            self.edges = []
            self.edges_at_node = {}

            distance_matrix = self.scenario.substrate.get_shortest_paths_cost_dict()
            distance_matrix_mb = {}
            distance_matrix_cp = {}

            for mb in self.middleboxes:
                distance_matrix_mb[mb] = []
            for cp in self.communication_pairs:
                distance_matrix_cp[cp] = []

            for mb in self.middleboxes:
                for cp in self.communication_pairs:
                    tail = self.scenario.requests[cp].tail
                    head = self.scenario.requests[cp].head

                    #print tail, head
                    #print distance_matrix[tail][head]
                    if distance_matrix[tail][mb] + distance_matrix[mb][head] <= ((1+self.scenario.requests[cp].max_deviation) * (distance_matrix[tail][head])):

                        dist_quo = distance_matrix[tail][mb] + distance_matrix[mb][head] / ((1+self.scenario.requests[cp].max_deviation) * (distance_matrix[tail][head] + 0.001))

                        distance_matrix_mb[mb].append((cp,dist_quo))

                        distance_matrix_cp[cp].append((mb,dist_quo))

                        self.edges.append((mb, cp))

            for mb in self.middleboxes:
                self.edges_at_node[mb] = sorted( distance_matrix_mb[mb], key=lambda x: x[1])
                self.edges_at_node[mb] = [(mb,x) for (x,y) in self.edges_at_node[mb]]
                #print self.edges_at_node[mb]

            for cp in self.communication_pairs:
                self.edges_at_node[cp] = sorted( distance_matrix_cp[cp], key=lambda x: x[1])
                self.edges_at_node[cp] = [(x,cp) for (x,y) in self.edges_at_node[cp]]
                #print self.edges_at_node[cp]



        else:
            self.edges = orig.edges
            self.edges_at_node = orig.edges_at_node


class StatefulMatchingGraph(MatchingGraph):


    def __init__(self, scenario, orig=None):
        super().__init__(scenario, orig)


        self.active_mbs = set()
        self.inactive_mbs = set()

        self.is_free_cp = {}
        self.edge_in_matching = set()

        self.available_capacity = {}

        self.size_of_matching = 0


        if orig is None:

            for cp in self.communication_pairs:
                self.is_free_cp[cp] = True

            for mb in self.middleboxes:
                self.inactive_mbs.add(mb)

            for mb in self.middleboxes:
                self.available_capacity[mb] = self.scenario.middleboxes[mb]

        else:

            self.size_of_matching = orig.size_of_matching

            self.edge_in_matching = orig.edge_in_matching.copy()

            for cp in self.communication_pairs:
                self.is_free_cp[cp] = orig.is_free_cp[cp]

            for mb in orig.inactive_mbs:
                self.inactive_mbs.add(mb)

            for mb in orig.active_mbs:
                self.active_mbs.add(mb)

            for mb in self.middleboxes:
                self.available_capacity[mb] = orig.available_capacity[mb]


    def reinitialize(self, orig):
        self.active_mbs.clear()
        self.inactive_mbs.clear()

        self.size_of_matching = orig.size_of_matching

        self.edge_in_matching = orig.edge_in_matching.copy()

        for cp in self.communication_pairs:
            self.is_free_cp[cp] = orig.is_free_cp[cp]

        for mb in orig.inactive_mbs:
            self.inactive_mbs.add(mb)

        for mb in orig.active_mbs:
            self.active_mbs.add(mb)

        for mb in self.middleboxes:
            self.available_capacity[mb] = orig.available_capacity[mb]

    def reinitialize_from_edges(self, active_edges):

        self.active_mbs.clear()

        self.inactive_mbs.clear()

        #print self.middleboxes

        for mb in self.middleboxes:
            self.inactive_mbs.add(mb)
            self.available_capacity[mb] = self.scenario.middleboxes[mb]

        for cp in self.communication_pairs:
            self.is_free_cp[cp] = True


        self.edge_in_matching = active_edges.copy()

        for (mb,cp) in active_edges:
            self.is_free_cp[cp] = False
            if mb not in self.active_mbs:
                self.active_mbs.add(mb)
            self.available_capacity[mb] -= 1

        self.size_of_matching = len(active_edges)


    def move_mb_to_active(self, mb):
        self.inactive_mbs.remove(mb)
        self.active_mbs.add(mb)

    def reduce_available_capacity_of_mb(self, mb):
        self.available_capacity[mb] -= 1

    def remove_cp_from_free_cps(self, cp):
        if self.is_free_cp[cp] is False:
            raise Exception("Cannot unfree a freed cp")
        self.is_free_cp[cp] = False
        self.size_of_matching += 1

    def get_size_of_matching(self):
        return len(self.edge_in_matching)

    def number_of_active_mbs(self):
        return len(self.active_mbs)

    def check_validity(self, all_cps_must_be_assigned=True):
        #1. check whether each pair is covered
        if all_cps_must_be_assigned:
            for cp in self.communication_pairs:
                found = False
                for (mb,cp) in self.edges_at_node[cp]:
                    #print "{} <--> {} : {}".format(mb, cp, self.edge_in_matching[(mb,cp)])
                    if (mb,cp) in self.edge_in_matching:
                        if found:
                            raise Exception("Same CP is assigned to multiple MBs")
                        found = True
                if not found:
                    print(cp)
                    print(self.edge_in_matching)
                    print(self.edges_at_node[cp])
                    raise Exception("CP is not assigned!")
        for mb in self.middleboxes:
            counter = 0
            for (mb,cp) in self.edges_at_node[mb]:
                if (mb,cp) in self.edge_in_matching:
                    counter += 1
            if mb not in self.active_mbs and counter > 0:
                raise Exception("Using an inactive mb!")
            if mb in self.active_mbs and counter > self.scenario.middleboxes[mb]:
                raise Exception("Capacity is violated!")


    def check_validity_weights(self, all_cps_must_be_assigned=True, check_capacity_violations=True):
        #1. check whether each pair is covered
        if all_cps_must_be_assigned:
            for cp in self.communication_pairs:
                found = False
                for (mb,cp) in self.edges_at_node[cp]:
                    #print "{} <--> {} : {}".format(mb, cp, self.edge_in_matching[(mb,cp)])
                    if (mb,cp) in self.edge_in_matching:
                        if found:
                            raise Exception("Same CP is assigned to multiple MBs")
                        found = True
                if not found:
                    print(cp)
                    print(self.edge_in_matching)
                    print(self.edges_at_node[cp])
                    raise Exception("CP is not assigned!")
        for mb in self.middleboxes:
            assigned_capacity = 0.0
            for (mb,cp) in self.edges_at_node[mb]:
                if (mb,cp) in self.edge_in_matching:
                    assigned_capacity += self.scenario.requests[cp].capacity
            if mb not in self.active_mbs and assigned_capacity > 0.0:
                raise Exception("Using an inactive mb!")
            if check_capacity_violations:
                if mb in self.active_mbs and assigned_capacity > 2.0*self.scenario.middleboxes[mb]:
                    raise Exception("Capacity is violated!")
