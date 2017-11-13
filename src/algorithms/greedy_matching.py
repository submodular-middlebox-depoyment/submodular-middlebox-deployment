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

from collections import deque

from algorithms import abstract_algorithm as aa_pkg
from datamodel import matching_graph as mg_pkg


class GreedyMatching(aa_pkg.AbstractAlgorithm):
    alg_name = "GreedySingle"

    def __init__(self, scenario):
        super().__init__(scenario)

        for req in self.scenario.requests:
            if req.capacity != 1:
                raise Exception("Requests must have a capacity of 1.")
        self.matching_graph = mg_pkg.StatefulMatchingGraph(scenario)
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

    def _run(self):

        while self.matching_graph.get_size_of_matching() < len(self.matching_graph.communication_pairs):
            next_matching = self._greedy_step()
            self.matching_graph.reinitialize(next_matching)
            self._save_history(next_matching)
            print(f"[{self.alg_name}]: current solution with {self.matching_graph.number_of_active_mbs()}"
                  f" many middleboxes covers {self.matching_graph.get_size_of_matching()} many cps")

        self.matching_graph.check_validity()
        print(f"[{self.alg_name}]: found solution with {self.matching_graph.number_of_active_mbs()} many middleboxes!")
        return self.matching_graph

    def _save_history(self, next_matching):
        pass

    def _greedy_step(self):

        current_optimum = None
        current_optimums_matching_size = 0
        for mb in self.matching_graph.inactive_mbs:
            tmp_mg = self._compute_maximal_matching(mb)
            if current_optimums_matching_size < tmp_mg.get_size_of_matching():
                self.current_optimum = tmp_mg
                current_optimums_matching_size = tmp_mg.get_size_of_matching()
        return self.current_optimum

    def _compute_maximal_matching(self, candidate_mb):

        tmp_mg = None

        if self.temp_matching_1 is not self.current_optimum:
            tmp_mg = self.temp_matching_1
            tmp_mg.reinitialize(self.matching_graph)
        elif self.temp_matching_2 is not self.current_optimum:
            tmp_mg = self.temp_matching_2
            tmp_mg.reinitialize(self.matching_graph)
        else:
            raise Exception("This should not happen!")

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

                node, matching_edge = self.Q.popleft()

                if matching_edge:
                    mb = node
                    for (mb, cp) in tmp_mg.edges_at_node[mb]:
                        if self.predecessors[cp] is not None or (mb, cp) in tmp_mg.edge_in_matching:
                            continue
                        self.Q.append((cp, False))
                        self.predecessors[cp] = mb
                        self.changed_predecessors.append(cp)
                else:
                    cp = node

                    if tmp_mg.is_free_cp[cp]:
                        found_free_cp = cp
                        break

                    for (mb, cp) in tmp_mg.edges_at_node[cp]:
                        if self.predecessors[mb] is not None or (mb, cp) not in tmp_mg.edge_in_matching:
                            continue
                        self.Q.append((mb, True))
                        self.predecessors[mb] = cp
                        self.changed_predecessors.append(mb)

            if found_free_cp is None:
                # we are done!
                break
            else:
                tmp_mg.remove_cp_from_free_cps(cp)

                current_node = found_free_cp
                matching_edge = True

                while self.predecessors[current_node] is not current_node:
                    edge = None
                    pred = self.predecessors[current_node]
                    if matching_edge:
                        edge = (pred, current_node)
                        tmp_mg.edge_in_matching.add(edge)
                    else:
                        edge = (current_node, pred)
                        tmp_mg.edge_in_matching.remove(edge)
                    matching_edge = not matching_edge
                    current_node = pred

                # current_node is now the initial middlebox
                tmp_mg.reduce_available_capacity_of_mb(current_node)

        return tmp_mg

    def _get_extra_information(self):
        return None
