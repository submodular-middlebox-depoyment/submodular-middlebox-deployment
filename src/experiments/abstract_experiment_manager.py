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
import enum
import os
import pickle
import random


class AlgorithmIdentifier:
    def __init__(self, key, properties=None):
        self.key = AlgorithmType(key)
        self.properties = properties
        self._hash = None
        self._str = None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.key == other.key and self.properties == other.properties
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        if self._hash is None:
            self._hash = ""
            if self.properties is not None:
                for key in sorted(self.properties.keys()):
                    self._hash += str(key) + ":" + str(self.properties[key]) + ","
            self._hash = str(self.key) + self._hash
            self._hash = self._hash.__hash__()
        return self._hash

    def __str__(self):
        if self._str is None:
            self._str = ""
            if self.properties is not None:
                self._str = " ("
                for key in sorted(self.properties.keys()):
                    self._str += str(key) + ":" + str(self.properties[key]) + ",  "
                self._str = self._str[0:-2] + ")"
            self._str = str(self.key) + self._str
        return self._str

    def __getstate__(self):
        return self.key, self.properties

    def __setstate__(self, state):
        self.key, self.properties = state
        self._hash = self._str = None


class AlgorithmType(enum.Enum):
    MIP = "MIP"
    GREEDY_SINGLE = "GREEDY_SINGLE"
    GREEDY_PARALLEL = "GREEDY_PARALLEL"


class AbstractAlgorithmManager(abc.ABC):
    default_algorithms = []

    def __init__(self):
        self.algorithms = []
        self.algorithm_partition = None

    def add_algorithm(self, algorithm_key, properties=None):
        algorithm = AlgorithmIdentifier(algorithm_key, properties)
        if algorithm in self.algorithms:
            raise Exception(f"Algorithm {algorithm_key} with properties {properties} already in use")
        self.algorithms.append(algorithm)

    def remove_algorithm(self, algorithm_key):
        for algorithm in self.algorithms:
            if algorithm.key == algorithm_key:
                self.algorithms.remove(algorithm)

    @classmethod
    def get_standard_algorithm_manager(cls):
        alg_mgr = cls()
        for alg in cls.default_algorithms:
            alg_mgr.add_algorithm(*alg)
        return alg_mgr

    @abc.abstractmethod
    def execute_algorithms_in_parallel(self, scenario, max_number_of_processes, *args):
        ...

    def execute_algorithm_multiprocess(self, scenario, algorithm, result_queue, *extra_parameters):
        alg = self.create_algorithm(scenario, algorithm, *extra_parameters)
        result = alg.run()
        result_queue.put([algorithm, result])

    @abc.abstractmethod
    def create_algorithm(self, scenario, algorithm, *extra_parameters):
        ...

    def get_algorithm_partition(self, max_number_parallel_processes):
        result = []

        process_count_to_alg = {}
        for alg in self.algorithms:
            process_count = 1
            if alg.key == AlgorithmType.GREEDY_SINGLE or alg.key == AlgorithmType.GREEDY_PARALLEL:
                if alg.key == AlgorithmType.GREEDY_PARALLEL:
                    process_count = alg.properties["processes"]
            if process_count not in process_count_to_alg:
                process_count_to_alg[process_count] = []
            process_count_to_alg[process_count].append(alg)

        process_counts = sorted(process_count_to_alg.keys(), reverse=True)

        while len(process_counts) > 0:

            available_count = max_number_parallel_processes
            partition = []
            print("starting a new partition")
            print(f"remaining elements are {process_count_to_alg} ")

            for i in process_counts:
                while available_count >= i and i in process_count_to_alg and len(process_count_to_alg[i]) > 0:
                    available_count -= i
                    partition.append(process_count_to_alg[i][0])
                    print(f"\tadding {process_count_to_alg[i][0]} to partition obtaining {partition}")
                    process_count_to_alg[i] = process_count_to_alg[i][1:]
                    if len(process_count_to_alg[i]) == 0:
                        del process_count_to_alg[i]
                    print(f"\tnew remaining algorithms {process_count_to_alg}")

            result.append(partition)
            process_counts = sorted(process_count_to_alg.keys(), reverse=True)

        return result


class AbstractExperimentManager(abc.ABC):
    algorithm_manager_class = None

    def __init__(self, probability_for_pair, max_deviation, capacity_factor,substrate_filter=None, number_of_repetitions=1, offset=0):
        self.probability_for_pair = probability_for_pair
        self.max_deviation = max_deviation
        self.capacity_factor = capacity_factor

        self.scenario_keys  = []
        self.scenarios = {}
        self.scenario_solutions = {}
        self.substrate_filter = substrate_filter
        self.number_of_repetitions = number_of_repetitions
        self.offset = 0

        self.algorithm_manager = self.algorithm_manager_class.get_standard_algorithm_manager()

        random.seed(1337)


def unpickle_experiment_manager(path):
    with open(path, "rb") as f:
        return pickle.loads(f.read())


def pickle_experiment_manager(experiment_manager, path):
    print(path)
    with open(path, "wb") as f:
        f.write(pickle.dumps(experiment_manager))
