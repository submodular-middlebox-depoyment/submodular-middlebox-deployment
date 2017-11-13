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

import gurobipy
from gurobipy import GRB

from algorithms import abstract_algorithm as aa_pkg
from algorithms.gurobi_status import GurobiStatus
from datamodel import matching_graph as mg_pkg


class Special_StatefulMatchingGraph:

    def __init__(self, scenario, active_mbs, mb_assignment_vars, classic_mg):

        self.scenario = scenario
        self.active_mbs = active_mbs
        self.mb_assignment_vars = mb_assignment_vars
        self.classic_mg = classic_mg

        self.communication_pairs = range(len(self.scenario.requests))
        self.middleboxes_unitary = self.scenario.middleboxes.keys()
        self.middlebox_copies = {}
        self.current_capacity = {}

        self.edges_at_node = {}

        self.middleboxes = []
        self.inactive_mbs = set(x for x in self.middleboxes_unitary if x not in self.active_mbs)
        self.available_capacity = {}

        for mb in self.active_mbs:
            mb_copy = (mb, 0)
            self.middlebox_copies[mb] = [mb_copy]
            self.current_capacity[mb] = 1.0
            self.available_capacity[mb_copy] = 1.0

            self.middleboxes.append(mb_copy)
            self.edges_at_node[mb_copy] = []

        for cp in self.communication_pairs:
            self.edges_at_node[cp] = []

        self.is_free_cp = {}
        self.edge_in_matching = set()

        self.size_of_matching = 0

        self.edges = []

        self.predecessors = {}
        self.Q = deque()
        self.changed_predecessors = []

    def run(self):
        self.initialize_matching_graph()
        self.compute_maximal_matching()

    def initialize_matching_graph(self):

        # for cp in self.communication_pairs:
        #     print "cp {}".format(cp)
        #     for (mb, _) in self.classic_mg.edges_at_node[cp]:
        #         if self.mb_assignment_vars[(mb,cp)].X > 0:
        #             print "\t mb\t{} \t --> {}".format(mb, self.mb_assignment_vars[(mb,cp)].X)


        for mb in self.active_mbs:
            attached_cps = [(cp,self.mb_assignment_vars[(mb,cp)].X, self.scenario.requests[cp].capacity)  for (_,cp) in self.classic_mg.edges_at_node[mb] if self.mb_assignment_vars[(mb,cp)].X > 0]
            attached_cps_sorted =sorted(attached_cps, key=lambda x_y_z: -x_y_z[2])

            #print "\n\nMB: {}\n\t{}\n".format(mb, attached_cps_sorted)

            if sum([assignment_var for (_,assignment_var,_) in attached_cps_sorted]) <= 1:
                current_mb_copy = self.middlebox_copies[mb][len(self.middlebox_copies[mb])-1]

                for (cp,assignment, weight) in attached_cps_sorted:
                    edge = (current_mb_copy, cp)
                    self.edges.append(edge)
                    self.edges_at_node[current_mb_copy].append(edge)
                    self.edges_at_node[cp].append(edge)

                    self.current_capacity[mb] -= min(assignment, self.current_capacity[mb])
            else:

                for (cp,assignment, weight) in attached_cps_sorted:

                    current_mb_copy = self.middlebox_copies[mb][len(self.middlebox_copies[mb])-1]

                    edge = (current_mb_copy, cp)
                    self.edges.append(edge)
                    self.edges_at_node[current_mb_copy].append(edge)
                    self.edges_at_node[cp].append(edge)

                    self.current_capacity[mb] -= min(assignment, self.current_capacity[mb])
                    assignment_new = assignment - min(assignment, self.current_capacity[mb])

                    if assignment_new > 0.0:
                        mb_copy = (mb, len(self.middlebox_copies[mb]))
                        self.middlebox_copies[mb].append(mb_copy)
                        self.current_capacity[mb] = 1.0

                        self.middleboxes.append(mb_copy)
                        self.available_capacity[mb_copy] = 1.0

                        self.edges_at_node[mb_copy] = []

                        edge = (mb_copy, cp)
                        self.edges.append(edge)
                        self.edges_at_node[mb_copy].append(edge)
                        self.edges_at_node[cp].append(edge)

                        self.current_capacity[mb] -= min(assignment_new, self.current_capacity[mb])


        for mb in self.middleboxes:
            self.predecessors[mb] = None
        for cp in self.communication_pairs:
            self.predecessors[cp] = None
            self.is_free_cp[cp] = True

    def compute_maximal_matching(self):

        while True:

            for node in self.changed_predecessors:
                self.predecessors[node] = None
            self.changed_predecessors[:] = []

            self.Q.clear()

            for mb in self.middleboxes:
                if self.available_capacity[mb] == 0:
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
                    for (mb,cp) in self.edges_at_node[mb]:
                        if self.predecessors[cp] is not None or (mb,cp) in self.edge_in_matching:
                            continue
                        self.Q.append((cp,False))
                        self.predecessors[cp] = mb
                        self.changed_predecessors.append(cp)
                else:
                    cp = node
                    #print "[compute matching] current CP: {}".format(node)
                    if self.is_free_cp[cp]:
                        found_free_cp = cp
                        break

                    for (mb,cp) in self.edges_at_node[cp]:
                        if self.predecessors[mb] is not None or (mb,cp) not in self.edge_in_matching:
                            continue
                        self.Q.append((mb, True))
                        self.predecessors[mb] = cp
                        self.changed_predecessors.append(mb)

            if found_free_cp is None:
                #we are done!
                break
            else:
                self.is_free_cp[cp] = False

                current_node = found_free_cp
                matching_edge = True

                while self.predecessors[current_node] is not current_node:
                    edge = None
                    pred = self.predecessors[current_node]
                    if matching_edge:
                        edge = (pred,current_node)
                        self.edge_in_matching.add(edge)
                    else:
                        edge = (current_node, pred)
                        self.edge_in_matching.remove(edge)
                    matching_edge = not matching_edge
                    current_node = pred

                #current_node is now the initial middlebox
                self.available_capacity[current_node] = 0.0

    def convert_to_classic_matching_graph(self):
        self.classic_mg.active_mbs = self.active_mbs

        self.classic_mg.inactive_mbs = self.inactive_mbs

        for cp in self.communication_pairs:
            matching_edge = None
            for (mb_copy, cp) in self.edges_at_node[cp]:
                if (mb_copy,cp) in self.edge_in_matching:
                    if not matching_edge is None:
                        raise Exception("There seem to be multiple assignments of a single cp!")
                    matching_edge = (mb_copy, cp)
            if matching_edge is None:
                raise Exception("A cp is not assigned: {} !".format(cp))

            mb, id = mb_copy
            self.classic_mg.edge_in_matching.add((mb,cp))

        for mb in self.middleboxes_unitary:

            mb_capacity = self.scenario.middleboxes[mb]
            active_capacity = 0.0
            for (mb_other,cp) in self.classic_mg.edge_in_matching:
                if mb == mb_other:
                    active_capacity += self.scenario.requests[cp].capacity

            print("for mb {:<20} \tthe used capacity is {} / {}".format(mb, active_capacity, mb_capacity))


            if active_capacity / mb_capacity > 1:

                print("\n\t\t\tVIOLATION BY {}\n".format(active_capacity / mb_capacity - 1))

                if active_capacity / mb_capacity > 2:
                    print("WARNING: THIS SEEMS WEIRD!")

        self.classic_mg.check_validity_weights(check_capacity_violations=False)
        return self.classic_mg






    # def move_mb_to_active(self, mb):
    #     self.inactive_mbs.remove(mb)
    #     self.active_mbs.add(mb)
    #
    # def reduce_available_capacity_of_mb(self, mb):
    #     self.available_capacity[mb] -= 1
    #
    # def remove_cp_from_free_cps(self, cp):
    #     if self.is_free_cp[cp] is False:
    #         raise Exception("Cannot unfree a freed cp")
    #     self.is_free_cp[cp] = False
    #     self.size_of_matching += 1
    #
    # def get_size_of_matching(self):
    #     return len(self.edge_in_matching)
    #
    # def number_of_active_mbs(self):
    #     return len(self.active_mbs)
    #
    # def check_validity(self, all_cps_must_be_assigned=True):
    #     #1. check whether each pair is covered
    #     if all_cps_must_be_assigned:
    #         for cp in self.communication_pairs:
    #             found = False
    #             for (mb,cp) in self.edges_at_node[cp]:
    #                 #print "{} <--> {} : {}".format(mb, cp, self.edge_in_matching[(mb,cp)])
    #                 if (mb,cp) in self.edge_in_matching:
    #                     if found:
    #                         raise Exception("Same CP is assigned to multiple MBs")
    #                     found = True
    #             if not found:
    #                 print cp
    #                 print self.edge_in_matching
    #                 print self.edges_at_node[cp]
    #                 raise Exception("CP is not assigned!")
    #     for mb in self.middleboxes:
    #         counter = 0
    #         for (mb,cp) in self.edges_at_node[mb]:
    #             if (mb,cp) in self.edge_in_matching:
    #                 counter += 1
    #         if not mb in self.active_mbs and counter > 0:
    #             raise Exception("Using an inactive mb!")
    #         if mb in self.active_mbs and counter > self.scenario.middleboxes[mb]:
    #             raise Exception("Capacity is violated!")

class Greedy_diff_weights(aa_pkg.AbstractAlgorithm_Diff_Weights):
    alg_name = "GreedyDiffWeights  "

    def __init__(self, scenario):
        super().__init__(scenario)

        self.mb_vars = {}
        self.mb_assignment_vars = {}
        self.model = None
        self.mg = mg_pkg.StatefulMatchingGraph(scenario)


    def construct_lp(self):

        self.model = gurobipy.Model("mb-deployment")

        for mb in self.mg.middleboxes:
            variableId = "mb_decision_{}".format(mb)
            self.mb_vars[mb] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.CONTINUOUS, name=variableId)
        for (mb, cp) in self.mg.edges:
            variableId = "mb_cp_assignment_{}_{}_{}".format(mb, self.scenario.requests[cp].tail, self.scenario.requests[cp].head)
            self.mb_assignment_vars[(mb,cp)] = self.model.addVar(lb=0.0, ub=1.0, obj=1.0, vtype=GRB.CONTINUOUS, name=variableId)


        self.model.update()

        for (mb, cp) in self.mg.edges:
            if self.scenario.middleboxes[mb] < self.scenario.requests[cp].capacity:
                self.mb_assignment_vars[(mb,cp)].ub = 0.0

        self.model.setObjective(self.model.getObjective(), GRB.MAXIMIZE)

        for cp in self.mg.communication_pairs:
            constr = gurobipy.LinExpr()
            for (mb,cp) in self.mg.edges_at_node[cp]:
                constr.addTerms(1.0, self.mb_assignment_vars[(mb,cp)])

            self.model.addConstr(constr, GRB.LESS_EQUAL, 1.0, name="covering_{}_{}".format(self.scenario.requests[cp].tail, self.scenario.requests[cp].head))

        for mb in self.mg.middleboxes:
            constr = gurobipy.LinExpr()
            for (mb,cp) in self.mg.edges_at_node[mb]:
                constr.addTerms(self.scenario.requests[cp].capacity, self.mb_assignment_vars[(mb,cp)])
            constr.addTerms(-1.0 * self.scenario.middleboxes[mb], self.mb_vars[mb])
            self.model.addConstr(constr, GRB.LESS_EQUAL, 0.0, name="upper_bound_{}".format(mb))

        for (mb,cp) in self.mg.edges:
            constr = gurobipy.LinExpr()
            constr.addTerms(1.0, self.mb_assignment_vars[(mb,cp)])
            constr.addTerms(-1.0, self.mb_vars[mb])
            self.model.addConstr(constr, GRB.LESS_EQUAL, 0.0, name="lower_bound_{}_{}_{}".format(mb, self.scenario.requests[cp].tail, self.scenario.requests[cp].head))

        #self.model.setParam("Method", 1)
        #self.model.setParam("Presolve", 0)
        self.model.setParam("Threads", 1)

        self.model.update()

        self.vars = self.model.getVars()
        self.constrs = self.model.getConstrs()

    def adapt_lp(self, allowed_mbs):

        for mb in self.scenario.middleboxes.keys():

            if mb in allowed_mbs:
                self.mb_vars[mb].lb = 1.0
                self.mb_vars[mb].ub = 1.0
            else:
                self.mb_vars[mb].lb = 0.0
                self.mb_vars[mb].ub = 0.0

        self.model.update()

    def get_current_basis(self):
        print("reading basis")
        pstart = [var.VBasis for var in self.vars]
        dstart = [cons.CBasis for cons in self.constrs]
        return pstart, dstart

    def set_basis(self, pstart, dstart):
        #print pstart, dstart
        print("setting basis")
        for index, var in enumerate(self.vars):
            var.VBasis = pstart[index]
        for index, cons in enumerate(self.constrs):
            cons.CBasis = dstart[index]





    def _run(self):

        self.construct_lp()

        self.installed_mbs = set()
        self.uninstalled_mbs = set(mb for mb in self.scenario.middleboxes.keys())

        #self.adapt_lp(self.installed_mbs)

        currently_connected_cps = 0.0

        pstart, dstart = None, None


        while len(self.scenario.requests) - currently_connected_cps > 0.99:

            print("\n\n\n HAVING INSTALLED \t {} \t many MBs serving \t {} \t of \t {} \t many connection pairs.\n\n\n".format(len(self.installed_mbs), currently_connected_cps, len(self.scenario.requests)))

            best_mb_to_open = None
            best_improvement = 0
            best_objval = None

            for uninstalled_mb in self.uninstalled_mbs:

                copy_of_installed_mbs = self.installed_mbs.copy()
                copy_of_installed_mbs.add(uninstalled_mb)

                self.adapt_lp(copy_of_installed_mbs)

                if pstart is not None:
                    pass
                    #self.set_basis(pstart, dstart)

                if not best_objval is None:
                    self.model.setParam("Cutoff", best_objval)

                self.model.optimize()

                #we just assume feasibility

                if self.model.getAttr("Status") != GurobiStatus.CUTOFF:

                    objval = self.model.getAttr("ObjVal")

                    if objval - currently_connected_cps > best_improvement:
                        best_improvement = objval - currently_connected_cps
                        best_mb_to_open = uninstalled_mb
                        best_objval = objval


            if not best_mb_to_open is None:
                self.installed_mbs.add(best_mb_to_open)
                self.uninstalled_mbs.remove(best_mb_to_open)

            #pstart, dstart = self.get_current_basis()


            currently_connected_cps = best_objval

        #recompute the optimal solution
        self.model.setParam("Cutoff", GRB.INFINITY)
        self.adapt_lp(self.installed_mbs)
        self.model.update()


        self.model.optimize()

        print("\n\n\n HAVING INSTALLED \t {} \t many MBs serving \t {} \t of \t {} \t many connection pairs.\n\n\n".format(len(self.installed_mbs), currently_connected_cps, len(self.scenario.requests)))

        extended_matching = Special_StatefulMatchingGraph(scenario=self.scenario, active_mbs=self.installed_mbs, mb_assignment_vars=self.mb_assignment_vars, classic_mg=self.mg)
        extended_matching.run()
        self.mg = extended_matching.convert_to_classic_matching_graph()
        return self.mg

    def _get_extra_information(self):
        return None
