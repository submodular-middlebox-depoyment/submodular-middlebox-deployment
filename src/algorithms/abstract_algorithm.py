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

import abc
import copy
import time


# algorithm results


class BaseAlgorithmResult:
    def __init__(self, alg_name, scenario):
        self.alg_name = alg_name
        self.scenario = scenario

    def __str__(self):
        return f"{self.alg_name} {self.scenario}"


class AlgorithmResult(BaseAlgorithmResult):
    def __init__(
            self,
            alg_name,
            scenario,
            active_mbs,
            matching_edges,
            runtime_with_init,
            runtime_without_init,
            extra_information):
        super().__init__(alg_name, scenario)
        self.active_mbs = active_mbs
        self.matching_edges = matching_edges
        self.runtime_with_init = runtime_with_init
        self.runtime_without_init = runtime_without_init
        self.extra_information = extra_information

    def __str__(self):
        return (f"{super().__str__()} {self.active_mbs} {self.matching_edges} {self.runtime_without_init}"
                f" {self.runtime_with_init} {self.extra_information}")


class AlgorithmResult_DiffWeights(AlgorithmResult):
    def __init__(
            self,
            alg_name,
            scenario,
            active_mbs,
            matching_edges,
            runtime_with_init,
            runtime_without_init,
            extra_information):
        super().__init__(alg_name, scenario, active_mbs, matching_edges, runtime_with_init, runtime_without_init,
                         extra_information)
        self.loads = self.get_loads()

    def get_loads(self):
        result = []
        for mb in self.active_mbs:
            mb_capacity = self.scenario.middleboxes[mb]
            active_capacity = 0.0
            for mb_other, cp in self.matching_edges:
                if mb == mb_other:
                    active_capacity += self.scenario.requests[cp].capacity
            result.append(active_capacity / mb_capacity)
        print(f"LOADS: {result}")
        # extracted the information necessary; forget about the underlying scenario!
        self.scenario = None
        return result


class IncrementalAlgorithmResult(BaseAlgorithmResult):
    def __init__(
            self,
            alg_name,
            scenario,
            probing_point,
            active_mbs_before,
            active_mbs_after,
            matching_edges_before,
            matching_edges_after,
            runtime_with_init,
            runtime_without_init,
            extra_information):
        super().__init__(alg_name, scenario)
        self.probing_point = probing_point
        self.active_mbs_before = active_mbs_before
        self.active_mbs_after = active_mbs_after
        self.matching_edges_before = matching_edges_before
        self.matching_edges_after = matching_edges_after
        self.runtime_with_init = runtime_with_init
        self.runtime_without_init = runtime_without_init
        self.extra_information = extra_information

    def get_relative_middlebox_relocation(self):
        active_mbs_after_copy = copy.deepcopy(self.active_mbs_after)
        active_mbs_after_copy = active_mbs_after_copy - self.active_mbs_before

        return len(active_mbs_after_copy) / len(self.active_mbs_after)

    def get_relative_reassignment(self):
        matching_edges_after_copy = copy.deepcopy(self.matching_edges_after)
        matching_edges_after_copy = matching_edges_after_copy - self.matching_edges_before

        return len(matching_edges_after_copy) / len(self.matching_edges_after)

    def __str__(self):
        return (f"{super().__str__()} {self.active_mbs_before} {self.active_mbs_after} {self.matching_edges_before}"
                f" {self.matching_edges_after} {self.runtime_without_init} {self.runtime_with_init}")


class IncrementalAlgorithmResult_mb_by_mb(BaseAlgorithmResult):
    def __init__(self, alg_name, scenario, matching_history):
        super().__init__(alg_name, scenario)
        self.matching_history = matching_history

    def get_maximal_number_of_mbs_needed(self):
        return max(self.matching_history.keys())

    def get_relative_middlebox_relocation(self, index):
        if index <= 1:
            raise Exception("Nothing to report here!")

        active_mbs_after_copy = copy.deepcopy(self.matching_history[index][0])
        active_mbs_after_copy = active_mbs_after_copy - self.matching_history[index - 1][0]

        return len(active_mbs_after_copy) / len(self.matching_history[index][0])

    def get_relative_reassignment(self, index):
        if index <= 1:
            raise Exception("Nothing to report here!")

        active_mbs_after_copy = copy.deepcopy(self.matching_history[index][1])
        active_mbs_after_copy = active_mbs_after_copy - self.matching_history[index - 1][1]

        return len(active_mbs_after_copy) / len(self.matching_history[index][1])

    def __str__(self):
        return f"{super().__str__()} {self.matching_history}"


# abstract algorithms


class AbstractAlgorithm(abc.ABC):
    alg_name: str  # set this in a subclass
    result_class = AlgorithmResult

    def __init__(self, scenario):
        self.scenario = scenario
        self.initialization_time = time.perf_counter()
        self.start_time = None
        self.end_time = None

    def run(self):
        self.start_time = time.perf_counter()
        matching_graph = self._run()
        self.end_time = time.perf_counter()

        print(f"ALGORITHM {self.alg_name} has returned {matching_graph}")

        if matching_graph is None:
            return None

        return self.result_class(alg_name=self.alg_name,
                                 scenario=self.scenario,
                                 active_mbs=matching_graph.active_mbs,
                                 matching_edges=matching_graph.edge_in_matching,
                                 runtime_with_init=self.end_time - self.initialization_time,
                                 runtime_without_init=self.end_time - self.start_time,
                                 extra_information=self._get_extra_information())

    @abc.abstractmethod
    def _run(self):
        ...

    @abc.abstractmethod
    def _get_extra_information(self):
        ...


class AbstractAlgorithm_Diff_Weights(AbstractAlgorithm):
    result_class = AlgorithmResult_DiffWeights
