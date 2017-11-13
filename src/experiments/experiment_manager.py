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

import gc
import itertools
import math
import multiprocessing
import random
import sys

from algorithms import (
    greedy_matching as greedy_pkg,
    greedy_matching_parallel as greedy_pkg_parallel,
    optimal_mip as mip_pkg,
)
from datamodel import (
    suitable_substrates as ss_pkg,
    scenario as scen_pkg,
    requests as req_pkg,
)
from experiments import abstract_experiment_manager as aem_pkg


class AlgorithmManager(aem_pkg.AbstractAlgorithmManager):
    default_algorithms = [
        ("MIP",),
        ("GREEDY_SINGLE",),
        ("GREEDY_PARALLEL", {"processes": 2}),
        ("GREEDY_PARALLEL", {"processes": 4}),
        ("GREEDY_PARALLEL", {"processes": 8}),
    ]

    def execute_algorithms_in_parallel(self, scenario, max_number_of_processes):
        results = {}
        result_queue = multiprocessing.Queue()

        if self.algorithm_partition is None:
            self.algorithm_partition = self.get_algorithm_partition(max_number_parallel_processes=max_number_of_processes)
        for alg_list in self.algorithm_partition:
            processes = {}
            for alg in alg_list:
                process = multiprocessing.Process(target=self.execute_algorithm_multiprocess, args=(scenario, alg, result_queue))
                print(f"starting {alg} .. ")
                process.start()
                processes[alg] = process
            for i in range(len(alg_list)):
                encapsulated_result = result_queue.get()
                print(f"received result {encapsulated_result}")
                encapsulated_result[1].scenario = scenario
                results[encapsulated_result[0]] = encapsulated_result[1]
                processes[encapsulated_result[0]].join()
                print(f"process of algorithm {encapsulated_result[0]} is terminated / {len(alg_list)-(i+1)} of {len(alg_list)} outstanding to terminate")

        return results

    def create_algorithm(self, scenario, algorithm):
        if algorithm.key == aem_pkg.AlgorithmType.MIP:
            return mip_pkg.ExactDeploymentMIP(scenario)
        elif algorithm.key == aem_pkg.AlgorithmType.GREEDY_SINGLE:
            return greedy_pkg.GreedyMatching(scenario)
        elif algorithm.key == aem_pkg.AlgorithmType.GREEDY_PARALLEL:
            return greedy_pkg_parallel.GreedyMatchingMaster(scenario, number_of_processes=algorithm.properties["processes"])
        else:
            raise Exception("I don't know this type of algorithm.")

    def get_algorithm_partition(self, max_number_parallel_processes):
        result = []

        process_count_to_alg = {}
        for alg in self.algorithms:
            process_count = 1
            if alg.key == aem_pkg.AlgorithmType.MIP:
                result.append([alg])
            elif alg.key == aem_pkg.AlgorithmType.GREEDY_SINGLE or alg.key == aem_pkg.AlgorithmType.GREEDY_PARALLEL:
                if alg.key == aem_pkg.AlgorithmType.GREEDY_PARALLEL:
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


class ExperimentManager(aem_pkg.AbstractExperimentManager):
    algorithm_manager_class = AlgorithmManager

    def __init__(self, probability_for_pair, max_deviation, capacity_factor,substrate_filter=None, number_of_repetitions=1, offset=0):
        super().__init__(probability_for_pair, max_deviation, capacity_factor,substrate_filter, number_of_repetitions, offset)
        self.suitable_substrates = ss_pkg.unpickle_pruned_suitable_substrates()


    def construct_scenarios(self):
        counter = 0
        print(self.probability_for_pair)
        print(self.capacity_factor)
        print(self.suitable_substrates)
        print(self.number_of_repetitions)
        print(self.max_deviation)

        for prob, cap_factor, substrate_name, repetition in itertools.product(self.probability_for_pair,
                                                                self.capacity_factor,
                                                                self.suitable_substrates.names,
                                                                range(self.number_of_repetitions)):

            #print self.substrate_filter
            if self.substrate_filter is not None and substrate_name not in self.substrate_filter:
                continue
            substrate = self.suitable_substrates.substrates[substrate_name]
            #print substrate_name
            pairs = []

            handled_nodes = []
            for u in substrate.nodes:
                handled_nodes.append(u)
                for v in substrate.nodes:
                    if v in handled_nodes:
                        continue
                    if random.random() <= prob:
                        pairs.append((u,v))
                        #req = req_pkg.Request(u, v, random.uniform(md_lb, md_ub), capacity=1)
                        #requests.append(req)

            for deviation in self.max_deviation:

                self.scenario_keys.append((prob, deviation, cap_factor, substrate_name, repetition))

                if counter > 0 and counter % 100 == 0:
                    if self.substrate_filter is not None:
                        print(f"Having created {counter} of {len(self.max_deviation) * len(self.capacity_factor) * len(self.probability_for_pair)*len(self.substrate_filter)*self.number_of_repetitions} many scenarios")
                    else:
                        print(f"Having created {counter} of {len(self.max_deviation) * len(self.capacity_factor) * len(self.probability_for_pair)*len(self.suitable_substrates.names)*self.number_of_repetitions} many scenarios")


                number_of_nodes = substrate.get_number_of_nodes()

                capacity = math.ceil((number_of_nodes - 1) * 2 * prob
                                     + (number_of_nodes * number_of_nodes - 2 * number_of_nodes - 1) / 2 * prob * cap_factor)

                requests = []



                md_lb, md_ub = deviation, deviation
                for (u,v) in pairs:
                    req = req_pkg.Request(u, v, random.uniform(md_lb, md_ub), capacity=1)
                    requests.append(req)


                middleboxes = {}
                for u in substrate.nodes:
                    middleboxes[u] = capacity

                scenario =  scen_pkg.Scenario(counter, substrate, requests, middleboxes)

                self.scenarios[(prob,deviation,cap_factor,substrate_name,repetition)] = scenario

                counter += 1

    def create_scenario_partition(self, number_of_servers):
        scenarios_of_server = {}
        for i in range(number_of_servers):
            scenarios_of_server[i] = []
        i = 0
        for x in self.scenario_keys:
            scenarios_of_server[i].append(x)
            i = (i+1)% number_of_servers
        return scenarios_of_server

    def execute_scenarios(self, server_number=None, number_of_servers=6, number_of_cores=8):
        scenario_keys = self.scenario_keys
        if server_number is None:
            print("\n\nWARNING: all experiments are executed now...\n\n")
        else:
            scenario_keys = self.create_scenario_partition(number_of_servers=number_of_servers)[server_number]

        counter = 1
        for scenario_key in scenario_keys:
            print(f"\n\nEXPERIMENT_MANAGER: Starting experiments for scenario {counter} of {len(scenario_keys)}\n\n")
            scen_results = self.algorithm_manager.execute_algorithms_in_parallel(self.scenarios[scenario_key], max_number_of_processes=number_of_cores)
            self.scenario_solutions[scenario_key] = scen_results
            counter += 1
            gc.collect()
            #import objgraph
            #objgraph.show_most_common_types()
            import resource
            print(f"Memory usage: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000} (MB)")
