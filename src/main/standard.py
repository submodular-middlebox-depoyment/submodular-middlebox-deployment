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

from evaluation import data_extractor as data_ext_pkg
from experiments import experiment_manager as exp_mgr_pkg

experiment_manager_class = exp_mgr_pkg.ExperimentManager
data_extractor_class = data_ext_pkg.DataExtractor


def create_experiment_manager_for_generation():
    probability_for_pair = [(i + 2) / 10 for i in range(3)]
    max_deviation = [i / 20 for i in range(31)]

    exp_mgr = experiment_manager_class(
        probability_for_pair=probability_for_pair,
        max_deviation=max_deviation,
        capacity_factor=[0.0],
        substrate_filter=['Quest', 'GtsHungary', 'Geant2012', 'Surfnet', 'Forthnet', 'Telcove', 'Ulaknet'],
        number_of_repetitions=15,
    )

    return exp_mgr
