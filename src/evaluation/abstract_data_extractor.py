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
import os
import pickle


class AbstractDataExtractor(abc.ABC):
    def __init__(self):
        self.scenario_keys = set()
        self.extracted_solution_data = {}
        self.algorithms_keys = set()
        self.topology_name_to_size = {}

    @abc.abstractmethod
    def extract_data_from_experiment_manager(self, exp_mgr):
        ...

    @abc.abstractmethod
    def print_it(self):
        ...


def unpickle_data_extractor(path):
    with open(path, "rb") as f:
        return pickle.loads(f.read())


def pickle_data_extractor(data_extractor, path):
    print(path)
    with open(path, "wb") as f:
        f.write(pickle.dumps(data_extractor))
