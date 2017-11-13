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

import gurobipy
from gurobipy import GRB

from algorithms import abstract_algorithm as aa_pkg
from algorithms.gurobi_status import GurobiStatus
from datamodel import matching_graph as mg_pkg


class ExactDeploymentMIP_diff_weights(aa_pkg.AbstractAlgorithm_Diff_Weights):
    alg_name = "OptimalMIP  "

    def __init__(self, scenario, mip_gap=0.001):
        super().__init__(scenario)

        self.mb_vars = {}
        self.mb_assignment_vars = {}
        self.model = None
        self.mg = mg_pkg.StatefulMatchingGraph(scenario)
        self.mip_gap = mip_gap


    def _run(self):
        self.model = gurobipy.Model("mb-deployment-weights")


        for mb in self.mg.middleboxes:
            variableId = "mb_decision_{}".format(mb)
            self.mb_vars[mb] = self.model.addVar(lb=0.0, ub=1.0, obj=1.0, vtype=GRB.BINARY, name=variableId)
        for (mb, cp) in self.mg.edges:
            variableId = "mb_cp_assignment_{}_{}_{}".format(mb, self.scenario.requests[cp].tail, self.scenario.requests[cp].head)
            self.mb_assignment_vars[(mb,cp)] = self.model.addVar(lb=0.0, ub=1.0, obj=0.0, vtype=GRB.BINARY, name=variableId)

        self.model.update()

        self.model.setObjective(self.model.getObjective(), GRB.MINIMIZE)

        for cp in self.mg.communication_pairs:
            constr = gurobipy.LinExpr()
            for (mb,cp) in self.mg.edges_at_node[cp]:
                constr.addTerms(1.0, self.mb_assignment_vars[(mb,cp)])
            self.model.addConstr(constr, GRB.EQUAL, 1.0, name="covering_{}_{}".format(self.scenario.requests[cp].tail, self.scenario.requests[cp].head))

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

        self.model.update()

        #self.model.write("diff_weights.lp")

        self.model.setParam("MIPGap", self.mip_gap)
        self.model.setParam("Threads", 1.0)

        self.model.optimize()

        if self.model.getAttr("SolCount") > 0.0:

            self.status = GurobiStatus(status=self.model.getAttr("Status"),
                                        solCount=self.model.getAttr("SolCount"),
                                        objValue=self.model.getAttr("ObjVal"),
                                        objGap=self.model.getAttr("MIPGap"),
                                        objBound=self.model.getAttr("ObjBound"),
                                        integralSolution=True)

            for mb in self.mg.middleboxes:
                if self.mb_vars[mb].X > 0.5:
                    self.mg.move_mb_to_active(mb)
            for (mb,cp) in self.mg.edges:
                if self.mb_assignment_vars[(mb,cp)].X > 0.5:
                    self.mg.edge_in_matching.add((mb,cp))
            self.mg.check_validity_weights()

            return self.mg

        return None

    def _get_extra_information(self):
        return None
