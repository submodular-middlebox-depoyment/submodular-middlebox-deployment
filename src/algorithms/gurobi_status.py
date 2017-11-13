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


class GurobiStatus:
    LOADED = 1  # Model is loaded, but no solution information is available.
    OPTIMAL = 2  # Model was solved to optimality (subject to tolerances), and an optimal solution is available.
    INFEASIBLE = 3  # Model was proven to be infeasible.
    INF_OR_UNBD = 4  # Model was proven to be either infeasible or unbounded. To obtain a more definitive conclusion, set the DualReductions parameter to 0 and reoptimize.
    UNBOUNDED = 5  # Model was proven to be unbounded. Important note: an unbounded status indicates the presence of an unbounded ray that allows the objective to improve without limit. It says nothing about whether the model has a feasible solution. If you require information on feasibility, you should set the objective to zero and reoptimize.
    CUTOFF = 6  # Optimal objective for model was proven to be worse than the value specified in the Cutoff parameter. No solution information is available.
    ITERATION_LIMIT = 7  # Optimization terminated because the total number of simplex iterations performed exceeded the value specified in the IterationLimit parameter, or because the total number of barrier iterations exceeded the value specified in the BarIterLimit parameter.
    NODE_LIMIT = 8  # Optimization terminated because the total number of branch-and-cut nodes explored exceeded the value specified in the NodeLimit parameter.
    TIME_LIMIT = 9  # Optimization terminated because the time expended exceeded the value specified in the TimeLimit parameter.
    SOLUTION_LIMIT = 10  # Optimization terminated because the number of solutions found reached the value specified in the SolutionLimit parameter.
    INTERRUPTED = 11  # Optimization was terminated by the user.
    NUMERIC = 12  # Optimization was terminated due to unrecoverable numerical difficulties.
    SUBOPTIMAL = 13  # Unable to satisfy optimality tolerances; a sub-optimal solution is available.
    IN_PROGRESS = 14  # A non-blocking optimization call was made (by setting the NonBlocking parameter to 1 in a Gurobi Compute Server environment), but the associated optimization run is not yet complete.

    def __init__(self,
                 status=1,
                 solCount=0,
                 objValue=gurobipy.GRB.INFINITY,
                 objBound=gurobipy.GRB.INFINITY,
                 objGap=gurobipy.GRB.INFINITY,
                 integralSolution=True
                 ):
        self.solCount = solCount
        self.status = status
        self.objValue = objValue
        self.objBound = objBound
        self.objGap = objGap
        self.integralSolution = integralSolution

    def _convertInfinityToNone(self, value):
        if value is gurobipy.GRB.INFINITY:
            return None
        return value

    def isIntegralSolution(self):
        return self.integralSolution

    def getObjectiveValue(self):
        return self._convertInfinityToNone(self.objValue)

    def getObjectiveBound(self):
        return self._convertInfinityToNone(self.objBound)

    def getMIPGap(self):
        return self._convertInfinityToNone(self.objGap)

    def hasFeasibleStatus(self):
        if self == GurobiStatus.INFEASIBLE:
            return False
        elif self == GurobiStatus.INF_OR_UNBD:
            return False
        elif self == GurobiStatus.UNBOUNDED:
            return False
        elif self == GurobiStatus.LOADED:
            return False
        return True

    def isFeasible(self):
        feasibleStatus = self.hasFeasibleStatus()
        result = feasibleStatus
        if not self.integralSolution and feasibleStatus:
            return True
        elif self.integralSolution:
            result = self.solCount > 0
            if result and not feasibleStatus:
                raise Exception(f"Solutions exist, but the status ({self.status}) indicated an infeasibility.")
            return result

        return result

    def isOptimal(self):
        if self.status == self.OPTIMAL:
            return True
        # elif not integralSolution and self.status == self.NODE_LIMIT:
        #    # pitfall: we use a node_limit to early terminate the LP relaxation process
        #    return True
        else:
            return False

    def __str__(self):
        return (f"solCount: {self.solCount}; "
                f"status: {self.status}; "
                f"objValue: {self.objValue}; "
                f"objBound: {self.objBound}; "
                f"objGap: {self.objGap}; "
                f"integralSolution: {self.integralSolution}; ")
