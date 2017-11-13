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

import copy
from collections import deque


from datamodel import matching_graph as mg_pkg

from algorithms import abstract_algorithm as aa_pkg

from algorithms import optimal_mip as mip_pkg


class IncrementalGreedyMatching(aa_pkg.AbstractAlgorithm):
    alg_name = "GreedySingle"

    def __init__(self, scenario, matching_edges, new_cp):
        super().__init__(scenario)

        for req in self.scenario.requests:
            if req.capacity != 1:
                raise Exception("Requests must have a capacity of 1.")
        self.matching_edges = matching_edges
        self.new_cp = new_cp

        self.scenario.requests.append(new_cp)
        self.scenario.add_single_request(new_cp)

        #print "CHECKING WHETHER THE MIP CAN SOLVE THE SCENARIO"
        #mip_alg = mip_pkg.ExactDeploymentMIP(scenario=scenario)
        #mip_alg.run()

        self.matching_graph = mg_pkg.StatefulMatchingGraph(scenario)

        self.matching_graph.reinitialize_from_edges(matching_edges)

        #print "SOME CHECKS"
        #print new_cp in self.scenario.requests
        #print new_cp
        #print self.scenario.requests
        #index_in_request_list = len(self.scenario.requests)-1
        #print index_in_request_list in self.matching_graph.communication_pairs
        #print index_in_request_list in self.matching_graph.edges_at_node
        #print "middleboxes ", self.matching_graph.middleboxes
        #print "active ones: ", self.matching_graph.active_mbs

        #for (mb, cp) in self.matching_graph.edges_at_node[index_in_request_list]:
        #    print "edge available: ", (mb, cp)
        #    print "middlebox is active? ", mb in self.matching_graph.active_mbs
        #    print "available capacity of mb ", self.matching_graph.available_capacity[mb]



        #print "XXX\n"
        #print len(self.matching_graph.edge_in_matching), " ", len(scenario.requests)

        self.current_optimum = None
        self.temp_matching_1 = mg_pkg.StatefulMatchingGraph(scenario)
        self.temp_matching_2 = mg_pkg.StatefulMatchingGraph(scenario)


        self.predecessors = {}
        self.Q = deque()
        self.changed_predecessors = []

        for mb in self.matching_graph.middleboxes:
            self.predecessors[mb] = None
        for cp in self.matching_graph.communication_pairs:
            self.predecessors[cp] = None

        #print "there exist {} many edges in the matching graph".format(len(self.matching_graph.edges))


    def _run(self):

        matching = self._extend_maximal_matching()

        if self.matching_graph.get_size_of_matching() < matching.get_size_of_matching():
            print("could extend the previous solution..")
            self.matching_graph.reinitialize(matching)
        else:
            print("could NOT extend the previous solution..")

        while self.matching_graph.get_size_of_matching() < len(self.matching_graph.communication_pairs):
            next_matching = self._greedy_step()
            if next_matching is None:
                raise Exception("Couldn't improve solution")
            self.matching_graph.reinitialize(next_matching)
            print("[{}]: current solution with {} many middleboxes covers {} many cps".format(self.alg_name, self.matching_graph.number_of_active_mbs(), self.matching_graph.get_size_of_matching()))

        self.matching_graph.check_validity()
        print("[{}]: found solution with {} many middleboxes!".format(self.alg_name, self.matching_graph.number_of_active_mbs()))
        return self.matching_graph

    def _greedy_step(self):

        current_optimum = None
        current_optimums_matching_size = self.matching_graph.size_of_matching
        for mb in self.matching_graph.inactive_mbs:
            tmp_mg = self._compute_maximal_matching(mb)
            if current_optimums_matching_size < tmp_mg.get_size_of_matching():
                self.current_optimum = tmp_mg
                current_optimums_matching_size = tmp_mg.get_size_of_matching()
        return self.current_optimum



    def _compute_maximal_matching(self, candidate_mb):


        tmp_mg = None

        #mg_pkg.StatefulMatchingGraph(self.scenario,orig=self.matching_graph)
        if self.temp_matching_1 is not self.current_optimum:
            tmp_mg = self.temp_matching_1
            tmp_mg.reinitialize(self.matching_graph)
        elif self.temp_matching_2 is not self.current_optimum:
            tmp_mg = self.temp_matching_2
            tmp_mg.reinitialize(self.matching_graph)
        else:
            raise Exception("This should not happen!")

        #print "matching_graph ", self.matching_graph
        #print "current_optimum", self.current_optimum
        #print "temp_matching_1", self.temp_matching_1
        #print "temp_matching_2", self.temp_matching_2
        #print "tmp_mg         ", tmp_mg


        tmp_mg.move_mb_to_active(candidate_mb)


        while True:

            for node in self.changed_predecessors:
                self.predecessors[node] = None
            self.changed_predecessors[:] = []

            self.Q.clear()

            for mb in tmp_mg.active_mbs:
                if tmp_mg.available_capacity[mb] == 0:
                    continue
                else:
                    self.Q.append((mb, True))
                    self.predecessors[mb] = mb
                    self.changed_predecessors.append(mb)

            found_free_cp = None



            while len(self.Q) > 0:

                (node, matching_edge) = self.Q.popleft()

                if matching_edge:
                    mb = node
                    #print "[compute matching] current MB: {}".format(node)
                    for (mb,cp) in tmp_mg.edges_at_node[mb]:
                        if self.predecessors[cp] is not None or (mb,cp) in tmp_mg.edge_in_matching:
                            continue
                        self.Q.append((cp,False))
                        self.predecessors[cp] = mb
                        self.changed_predecessors.append(cp)
                else:
                    cp = node
                    #print "[compute matching] current CP: {}".format(node)
                    if tmp_mg.is_free_cp[cp]:
                        found_free_cp = cp
                        break

                    for (mb,cp) in tmp_mg.edges_at_node[cp]:
                        if self.predecessors[mb] is not None or (mb,cp) not in tmp_mg.edge_in_matching:
                            continue
                        self.Q.append((mb, True))
                        self.predecessors[mb] = cp
                        self.changed_predecessors.append(mb)

            if found_free_cp is None:
                #we are done!
                break
            else:
                tmp_mg.remove_cp_from_free_cps(cp)

                current_node = found_free_cp
                matching_edge = True

                while self.predecessors[current_node] is not current_node:
                    edge = None
                    pred = self.predecessors[current_node]
                    if matching_edge:
                        edge = (pred,current_node)
                        tmp_mg.edge_in_matching.add(edge)
                    else:
                        edge = (current_node, pred)
                        tmp_mg.edge_in_matching.remove(edge)
                    matching_edge = not matching_edge
                    current_node = pred

                #current_node is now the initial middlebox
                tmp_mg.reduce_available_capacity_of_mb(current_node)

        return tmp_mg


    def _extend_maximal_matching(self):


        tmp_mg = None

        #mg_pkg.StatefulMatchingGraph(self.scenario,orig=self.matching_graph)
        if self.temp_matching_1 is not self.current_optimum:
            tmp_mg = self.temp_matching_1
            tmp_mg.reinitialize(self.matching_graph)
        elif self.temp_matching_2 is not self.current_optimum:
            tmp_mg = self.temp_matching_2
            tmp_mg.reinitialize(self.matching_graph)
        else:
            raise Exception("This should not happen!")

        #print "matching_graph ", self.matching_graph
        #print "current_optimum", self.current_optimum
        #print "temp_matching_1", self.temp_matching_1
        #print "temp_matching_2", self.temp_matching_2
        #print "tmp_mg         ", tmp_mg


        while True:

            for node in self.changed_predecessors:
                self.predecessors[node] = None
            self.changed_predecessors[:] = []

            self.Q.clear()

            for mb in tmp_mg.active_mbs:
                if tmp_mg.available_capacity[mb] == 0:
                    continue
                else:
                    self.Q.append((mb, True))
                    self.predecessors[mb] = mb
                    self.changed_predecessors.append(mb)

            found_free_cp = None



            while len(self.Q) > 0:

                (node, matching_edge) = self.Q.popleft()

                if matching_edge:
                    mb = node
                    #print "[extend matching] current MB: {}".format(node)
                    for (mb,cp) in tmp_mg.edges_at_node[mb]:
                        if self.predecessors[cp] is not None or (mb,cp) in tmp_mg.edge_in_matching:
                            continue
                        self.Q.append((cp,False))
                        self.predecessors[cp] = mb
                        self.changed_predecessors.append(cp)
                else:
                    cp = node
                    #print "[extend matching] current CP: {}".format(node)
                    if tmp_mg.is_free_cp[cp]:
                        found_free_cp = cp
                        break

                    for (mb,cp) in tmp_mg.edges_at_node[cp]:
                        if self.predecessors[mb] is not None or (mb,cp) not in tmp_mg.edge_in_matching:
                            continue
                        self.Q.append((mb, True))
                        self.predecessors[mb] = cp
                        self.changed_predecessors.append(mb)

            if found_free_cp is None:
                #we are done!
                break
            else:
                tmp_mg.remove_cp_from_free_cps(cp)

                current_node = found_free_cp
                matching_edge = True

                while self.predecessors[current_node] is not current_node:
                    edge = None
                    pred = self.predecessors[current_node]
                    if matching_edge:
                        edge = (pred,current_node)
                        tmp_mg.edge_in_matching.add(edge)
                    else:
                        edge = (current_node, pred)
                        tmp_mg.edge_in_matching.remove(edge)
                    matching_edge = not matching_edge
                    current_node = pred

                #current_node is now the initial middlebox
                tmp_mg.reduce_available_capacity_of_mb(current_node)

        return tmp_mg

    def _get_extra_information(self):
        return None




