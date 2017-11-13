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
import multiprocessing
import random

from algorithms import (
    greedy_diff_weights as greedy_pkg,
    optimal_mip_diff_weights as mip_pkg,
)
from datamodel import (
    scenario as scen_pkg,
    requests as req_pkg,
    sndlib_reader as sndlib_pkg,
)
from experiments import abstract_experiment_manager as aem_pkg


class AlgorithmManager(aem_pkg.AbstractAlgorithmManager):
    default_algorithms = [
        ("MIP",),
        ("GREEDY_SINGLE",),
    ]

    def execute_algorithms_in_parallel(self, scenario, max_number_of_processes):
        results = {}
        result_queue = multiprocessing.Queue()

        if self.algorithm_partition is None:
            self.algorithm_partition = self.get_algorithm_partition(max_number_parallel_processes=max_number_of_processes)
        requests_copy = copy.deepcopy(scenario.requests)

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
                simple_result = encapsulated_result[1]

                results[encapsulated_result[0]] = simple_result
                processes[encapsulated_result[0]].join()
                print(f"process of algorithm {encapsulated_result[0]} is terminated / {len(alg_list)-(i+1)} of {len(alg_list)} outstanding to terminate")

        return results

    def create_algorithm(self, scenario, algorithm):
        if algorithm.key == aem_pkg.AlgorithmType.MIP:
            return mip_pkg.ExactDeploymentMIP_diff_weights (scenario)
        elif algorithm.key == aem_pkg.AlgorithmType.GREEDY_SINGLE:
            return greedy_pkg.Greedy_diff_weights(scenario)
        elif algorithm.key == aem_pkg.AlgorithmType.GREEDY_PARALLEL:
            raise Exception("Cannot handle this!")
        else:
            raise Exception("I don't know this type of algorithm.")


class DiffWeightsExperimentManager(aem_pkg.AbstractExperimentManager):
    algorithm_manager_class = AlgorithmManager


    def construct_scenarios(self, test_scenarios_a_priori=True):
        counter = 0
        print(self.probability_for_pair)
        print(self.capacity_factor)
        print(self.number_of_repetitions)
        print(self.max_deviation)


        prototypical_scenarios = {}
        for substrate_name in self.substrate_filter:
            scenario = sndlib_pkg.create_scenario_from_sndlib_instance(substrate_name)
            prototypical_scenarios[substrate_name] = scenario

        for prob, cap_factor, substrate_name, repetition in itertools.product(self.probability_for_pair,
                                                                self.capacity_factor,
                                                                self.substrate_filter,
                                                                range(self.number_of_repetitions)):

            prototypical_scenario = prototypical_scenarios[substrate_name]
            substrate = prototypical_scenario.substrate

            print(f"\n\n\n\n\nstarting to generate {prob} {cap_factor} {substrate_name} {repetition}\n\n\n\n\n")

            while True:

                #print substrate_name
                pairs = []

                handled_nodes = []
                for req in prototypical_scenario.requests:
                    if random.random() <= prob:
                        pairs.append((req.tail, req.head, req.capacity))


                print(pairs)

                successful_generation = False

                for deviation in self.max_deviation:

                    if counter > 0 and counter % 100 == 0:
                        if self.substrate_filter is not None:
                            print(f"Having created {counter} of {len(self.max_deviation) * len(self.capacity_factor) * len(self.probability_for_pair)*len(self.substrate_filter)*self.number_of_repetitions} many scenarios")
                        else:
                            print(f"Having created {counter} of {len(self.max_deviation) * len(self.capacity_factor) * len(self.probability_for_pair)*len(self.suitable_substrates.names)*self.number_of_repetitions} many scenarios")


                    number_of_nodes = substrate.get_number_of_nodes()

                    requests = []

                    cum_capacity = 0.0
                    md_lb, md_ub = deviation, deviation
                    for (u,v, cap) in pairs:
                        req = req_pkg.Request(u, v, random.uniform(md_lb, md_ub), capacity=cap)
                        requests.append(req)

                        cum_capacity += cap

                    capacity = 4 * cum_capacity / number_of_nodes


                    middleboxes = {}
                    for u in substrate.nodes:
                        middleboxes[u] = capacity

                    scenario =  scen_pkg.Scenario(counter, substrate, requests, middleboxes)

                    #util_pkg.prettyPrint(scenario)

                    if deviation == self.max_deviation[0]:
                        mip = mip_pkg.ExactDeploymentMIP_diff_weights(scenario, mip_gap=1.0)
                        result = mip.run()
                        if result is not None:
                            successful_generation = True
                        else:
                            break


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


        for i in range(number_of_servers):
            for j in range(i+1,number_of_servers):
                for scenario_key in scenarios_of_server[i]:
                    if scenario_key in scenarios_of_server[j]:
                        raise Exception("Partition is not a partition!")

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
                                                                                 max_number_of_processes=number_of_cores)

            self.scenario_solutions[scenario_key] = scen_results

            counter += 1
            gc.collect()
            #import objgraph
            #objgraph.show_most_common_types()
            import resource
            print(f"Memory usage: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000} (MB)")
