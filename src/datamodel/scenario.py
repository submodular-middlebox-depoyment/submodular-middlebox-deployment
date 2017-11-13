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

class Scenario:

    def __init__(self, id, substrate, requests, middleboxes):
        """ facilities is a dictionary mapping nodes onto capacities   """

        self.id = id
        self.substrate = substrate
        self.requests = requests
        self.communication_pairs_at_node = {}
        self.middleboxes = middleboxes

        for req in requests:
            self.add_single_request(req)

    def add_single_request(self, req):
        tail = req.tail
        head = req.head
        if tail not in self.communication_pairs_at_node:
            self.communication_pairs_at_node[tail] = []
        if head not in self.communication_pairs_at_node:
            self.communication_pairs_at_node[head] = []

        self.communication_pairs_at_node[tail].append(req)
        self.communication_pairs_at_node[head].append(req)

    def print_it(self):
        print("\nScenario is as follows..\n")
        print("substrate graph has {} many nodes and {} many edges".format(len(self.substrate.nodes), len(self.substrate.edges)))
        print("there exist {} many communication requests".format(len(self.requests)))
        print("there exist {} many middlebox locations".format(len(self.middleboxes.keys())))
