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

from evaluation.abstract_data_extractor import AbstractDataExtractor


class IncrementalDataExtractor(AbstractDataExtractor):
    def __init__(self):
        super().__init__()
        self.probing_points = set()

    def extract_data_from_experiment_manager(self, exp_mgr):
        for scenario_key, algorithm_dict in exp_mgr.scenario_solutions.items():
            if scenario_key in self.scenario_keys:
                raise Exception(f"Already have stored the data for the scenario key {scenario_key}")

            topology_name = scenario_key[3]
            if topology_name not in self.topology_name_to_size:
                self.topology_name_to_size[topology_name] = exp_mgr.suitable_substrates.names_to_nodes[topology_name]

            if scenario_key[5] not in self.probing_points:
                self.probing_points.add(scenario_key[5])

            self.extracted_solution_data[scenario_key] = {}

            self.scenario_keys.add(scenario_key)
            for algorithm_id, algorithm_result in algorithm_dict.items():
                self.algorithms_keys.add(algorithm_id)

                self.extracted_solution_data[scenario_key][algorithm_id] = algorithm_result

    def check_completeness(self, other_scenario_keys=None):

        print("Starting check of completeness..")

        flattened_scenario_keys = [tuple(a[:5]) for a in self.scenario_keys]
        print(flattened_scenario_keys)
        flattened_scenario_keys = set(flattened_scenario_keys)

        if other_scenario_keys is not None:
            copy_of_scenario_keys = copy.deepcopy(flattened_scenario_keys)

            for other_scenario_key in flattened_scenario_keys:
                if other_scenario_key not in copy_of_scenario_keys:
                    raise Exception(f"DataExtractor has no information for scenario key {other_scenario_key}")

                copy_of_scenario_keys.remove(other_scenario_key)

            if len(copy_of_scenario_keys) > 0:
                for copy_key in copy_of_scenario_keys:
                    raise Exception(f"Scenario keys  was found in data but not in the given set of scenario_keys"
                                    f" (overall {copy_key} many unknown items)")

            for x in flattened_scenario_keys:
                for probing_point in self.probing_points:
                    if tuple(x[:5]) + (probing_point,) not in self.scenario_keys:
                        raise Exception("invalid probing points")

        print("\tsets of scenario keys are identical! ")

        for scenario_key in self.scenario_keys:
            for algorithm_id in self.algorithms_keys:
                if algorithm_id not in self.extracted_solution_data[scenario_key]:
                    raise Exception(f"Missing information for algorithm {algorithm_id} for scenario key {scenario_key}"
                                    f" (overall {len(self.algorithms_keys)} many algorithms were detected)")

        print("\ta single result for each algorithm! ")

    def print_it(self):
        print("Printing data extractor contents...")
        for scenario_key in self.scenario_keys:
            print(f"\t{scenario_key}..")
            for algorithm_id in self.algorithms_keys:
                extracted_data = self.extracted_solution_data[scenario_key][algorithm_id]
                print(f"\t\t{extracted_data}")