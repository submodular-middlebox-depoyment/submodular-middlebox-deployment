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
import gc
import itertools
import math
import multiprocessing
import random
import sys

from algorithms import (
    incremental_greedy_matching as greedy_pkg,
    incremental_optimal_mip as mip_pkg,
    optimal_mip as std_mip_pkg,
    abstract_algorithm as aa_pkg,
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
    ]

    def execute_algorithms_in_parallel(self, scenario, max_number_of_processes, probing_points):
        results = {}
        result_queue = multiprocessing.Queue()

        if self.algorithm_partition is None:
            self.algorithm_partition = self.get_algorithm_partition(max_number_parallel_processes=max_number_of_processes)
        requests_copy = copy.deepcopy(scenario.requests)
        for probing_point in probing_points:

            print(f"computing result for probing point {probing_point}..")

            results[probing_point] = {}


            boundary = int(math.ceil(probing_point*len(requests_copy)))
            if boundary == len(requests_copy):
                boundary -= 1
            scenario.requests = requests_copy[0:boundary]
            new_cp = requests_copy[boundary]
            mip_alg = std_mip_pkg.ExactDeploymentMIP(scenario)
            matching_graph = mip_alg._run()
            matching_edges = matching_graph.edge_in_matching

            for alg_list in self.algorithm_partition:

                processes = {}
                for alg in alg_list:
                    process = multiprocessing.Process(target=self.execute_algorithm_multiprocess, args=(scenario, alg, result_queue, new_cp, matching_edges))
                    print(f"starting {alg} .. ")
                    process.start()
                    processes[alg] = process
                for i in range(len(alg_list)):
                    encapsulated_result = result_queue.get()
                    print(f"received result {encapsulated_result}")
                    encapsulated_result[1].scenario = scenario
                    simple_result = encapsulated_result[1]

                    incremental_result = aa_pkg.IncrementalAlgorithmResult(alg_name=simple_result.alg_name,
                                                                           scenario=scenario,
                                                                           probing_point=probing_point,
                                                                           active_mbs_before=matching_graph.active_mbs,
                                                                           active_mbs_after=simple_result.active_mbs,
                                                                           matching_edges_before=matching_graph.edge_in_matching,
                                                                           matching_edges_after=simple_result.matching_edges,
                                                                           runtime_with_init=simple_result.runtime_with_init,
                                                                           runtime_without_init=simple_result.runtime_without_init,
                                                                           extra_information=simple_result.extra_information)

                    results[probing_point][encapsulated_result[0]] = incremental_result
                    processes[encapsulated_result[0]].join()
                    print(f"process of algorithm {encapsulated_result[0]} is terminated / {len(alg_list)-(i+1)} of {len(alg_list)} outstanding to terminate")
        return results

    def create_algorithm(self, scenario, algorithm, new_cp, active_edges_of_previous_solution):
        if algorithm.key == aem_pkg.AlgorithmType.MIP:
            return mip_pkg.IncrementalExactDeploymentMIP(scenario, active_edges_of_previous_solution, new_cp)
        elif algorithm.key == aem_pkg.AlgorithmType.GREEDY_SINGLE:
            return greedy_pkg.IncrementalGreedyMatching(scenario, active_edges_of_previous_solution, new_cp)
        elif algorithm.key == aem_pkg.AlgorithmType.GREEDY_PARALLEL:
            raise Exception("Cannot handle this!")
        else:
            raise Exception("I don't know this type of algorithm.")


class IncrementalExperimentManager(aem_pkg.AbstractExperimentManager):
    algorithm_manager_class = AlgorithmManager

    def __init__(self, probing_points, probability_for_pair, max_deviation, capacity_factor,substrate_filter=None, number_of_repetitions=1, offset=0):
        super().__init__(probability_for_pair, max_deviation, capacity_factor,substrate_filter, number_of_repetitions, offset)
        self.probing_points = probing_points
        self.suitable_substrates = ss_pkg.unpickle_pruned_suitable_substrates()


    def construct_scenarios(self, test_scenarios_a_priori=True):
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

            while True:

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

                successful_generation = False

                for deviation in self.max_deviation:



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

                    if deviation == self.max_deviation[0]:
                        mip = std_mip_pkg.ExactDeploymentMIP(scenario)
                        result = mip.run()
                        if result is not None:
                            successful_generation = True






                    self.scenario_keys.append((prob, deviation, cap_factor, substrate_name, repetition))
                    self.scenarios[(prob,deviation,cap_factor,substrate_name,repetition)] = scenario

                    counter += 1
                if successful_generation:
                    break

    def create_scenario_partition(self, number_of_servers):
        scenarios_of_server = {}
        for i in range(number_of_servers):
            scenarios_of_server[i] = []
        i = 0
        for x in self.scenario_keys:
            scenarios_of_server[i].append(x)
            i = (i+1)% number_of_servers
        for i in range(number_of_servers):
            print(f"i {i} --> ", scenarios_of_server[i])

        return scenarios_of_server

    def execute_scenarios(self, server_number=None, number_of_servers=6, number_of_cores=8, scenario_key_overwrite=None):
        scenario_keys = self.scenario_keys
        if scenario_key_overwrite is None:
            if server_number is None:
                print("\n\nWARNING: all experiments are executed now...\n\n")
            else:
                scenario_keys = self.create_scenario_partition(number_of_servers=number_of_servers)[server_number]
        else:
            scenario_keys = scenario_key_overwrite
        counter = 1
        for scenario_key in scenario_keys:
            print(f"\n\nEXPERIMENT_MANAGER: Starting experiments for scenario {counter} of {len(scenario_keys)}\n\n")
            scen_results = self.algorithm_manager.execute_algorithms_in_parallel(self.scenarios[scenario_key],
                                                                                 max_number_of_processes=number_of_cores,
                                                                                 probing_points=self.probing_points)

            for probing_point in scen_results.keys():
                self.scenario_solutions[tuple(scenario_key) + (probing_point,)] = scen_results[probing_point]

            counter += 1
            gc.collect()
            #import objgraph
            #objgraph.show_most_common_types()
            import resource
            print(f"Memory usage: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000} (MB)")
            print(self.scenario_solutions)
