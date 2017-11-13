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

from multiprocessing import Process, Queue, Lock
from collections import deque

from datamodel import matching_graph as mg_pkg
from algorithms import abstract_algorithm as aa_pkg

class GreedyMatchingSlave:

    def __init__(self, scenario):
        self.scenario = scenario
        for req in self.scenario.requests:
            if req.capacity != 1:
                raise Exception("Requests must have a capacity of 1.")
        self.matching_graph = mg_pkg.StatefulMatchingGraph(scenario)
        self.current_optimum = None
        self.temp_matching_1 = mg_pkg.StatefulMatchingGraph(scenario)
        self.temp_matching_2 = mg_pkg.StatefulMatchingGraph(scenario)

        self.predecessors = {}
        self.Q = deque()
        self.changed_predecessors = []

        self.current_optimums_matching_size = 0

        for mb in self.matching_graph.middleboxes:
            self.predecessors[mb] = None
        for cp in self.matching_graph.communication_pairs:
            self.predecessors[cp] = None

    def run(self):

        while self.matching_graph.get_size_of_matching() < len(self.matching_graph.communication_pairs):
            next_matching = self._greedy_step()
            self.matching_graph.reinitialize(next_matching)
            #  self.matching_graph.get_size_of_matching()

        self.matching_graph.check_validity()
        print("Greedy found solution with {} many middleboxes!".format(self.matching_graph.number_of_active_mbs()))


    def greedy_step(self, mb):
        #print "trying to incorporate mb {}".format(mb)
        tmp_mg = self._compute_maximal_matching(mb)
        #print "\n\ntrying to include {}".format(mb)
        #print self.current_optimums_matching_size
        #print tmp_mg.get_size_of_matching()
        if self.current_optimums_matching_size < tmp_mg.get_size_of_matching():
            self.current_optimum = tmp_mg
            self.current_optimums_matching_size = tmp_mg.get_size_of_matching()
        #print self.current_optimums_matching_size
        #print tmp_mg.get_size_of_matching()

    def reinitialize_matching_graph(self, new_matching_graph):
        self.matching_graph.reinitialize(new_matching_graph)
        self.current_optimum = None
        self.current_optimums_matching_size = 0

    def reinitialize_matching_graph_from_edges(self, active_edges):
        self.matching_graph.reinitialize_from_edges(active_edges)
        self.current_optimum = None
        self.current_optimums_matching_size = 0



    def _compute_maximal_matching(self, candidate_mb):


        tmp_mg = None

        #mg_pkg.StatefulMatchingGraph(self.scenario,orig=self.matching_graph)
        if self.temp_matching_1 is not self.current_optimum:
            tmp_mg = self.temp_matching_1
            tmp_mg.reinitialize(self.matching_graph)
        elif self.temp_matching_2 is not self.current_optimum:
            tmp_mg = self.temp_matching_2
            tmp_mg.reinitialize(self.matching_graph)
        else:
            raise Exception("This should not happen!")

        #print "matching_graph ", self.matching_graph
        #print "current_optimum", self.current_optimum
        #print "temp_matching_1", self.temp_matching_1
        #print "temp_matching_2", self.temp_matching_2
        #print "tmp_mg         ", tmp_mg


        tmp_mg.move_mb_to_active(candidate_mb)


        while True:

            for node in self.changed_predecessors:
                self.predecessors[node] = None
            self.changed_predecessors[:] = []

            self.Q.clear()

            for mb in tmp_mg.active_mbs:
                if tmp_mg.available_capacity[mb] == 0:
                    continue
                else:
                    self.Q.append((mb, True))
                    self.predecessors[mb] = mb
                    self.changed_predecessors.append(mb)

            found_free_cp = None



            while len(self.Q) > 0:

                (node, matching_edge) = self.Q.popleft()

                if matching_edge:
                    mb = node
                    for (mb,cp) in tmp_mg.edges_at_node[mb]:
                        if self.predecessors[cp] is not None or (mb,cp) in tmp_mg.edge_in_matching:
                            continue
                        #print "progress mb"
                        self.Q.append((cp,False))
                        self.predecessors[cp] = mb
                        self.changed_predecessors.append(cp)
                else:
                    cp = node

                    if tmp_mg.is_free_cp[cp]:
                        found_free_cp = cp
                        break

                    for (mb,cp) in tmp_mg.edges_at_node[cp]:
                        if self.predecessors[mb] is not None or (mb,cp) not in tmp_mg.edge_in_matching:
                            continue
                        #print "progress cp"
                        self.Q.append((mb, True))
                        self.predecessors[mb] = cp
                        self.changed_predecessors.append(mb)

            if found_free_cp is None:
                #we are done!
                break
            else:
                tmp_mg.remove_cp_from_free_cps(cp)

                current_node = found_free_cp
                matching_edge = True
                #print "matching edge"

                while self.predecessors[current_node] != current_node:
                    #print "resolution step"
                    edge = None
                    pred = self.predecessors[current_node]
                    #print "A: pred, current: {} {}".format(pred, current_node)
                    if matching_edge:
                        edge = (pred,current_node)
                        tmp_mg.edge_in_matching.add(edge)
                    else:
                        edge = (current_node, pred)
                        tmp_mg.edge_in_matching.remove(edge)
                    matching_edge = not matching_edge
                    current_node = pred
                    #print "B: pred, current: {} {}".format(current_node, self.predecessors[pred])
                #print tmp_mg.edge_in_matching

                #print tmp_mg.available_capacity

                #current_node is now the initial middlebox
                tmp_mg.reduce_available_capacity_of_mb(current_node)

        return tmp_mg



class WorkerMetaData:

    def __init__(self, greedy_worker_class, process, task_queue, input_queue, result_queue):
        self.greedy_worker_class = greedy_worker_class
        self.process = process
        self.task_queue = task_queue
        self.input_queue = input_queue
        self.result_queue = result_queue



def slave_execution(meta_data):

    while True:

        input = meta_data.input_queue.get()
        #print input
        if input is not None:
            meta_data.greedy_worker_class.reinitialize_matching_graph_from_edges(input)
        else:
            break

        while True:
            mb = meta_data.task_queue.get()
            #task may either be a real task or the command to terminate (first the tasks are written, then the command to end and then the input to free them)
            #i.e. execute task or exit loop
            if mb is not None:
                meta_data.greedy_worker_class.greedy_step(mb)
            else:
                break
        #print "worker...", meta_data.greedy_worker_class.current_optimum
        #send result back
        if meta_data.greedy_worker_class.current_optimum is None:
            meta_data.result_queue.put(None)
        else:
            meta_data.result_queue.put(meta_data.greedy_worker_class.current_optimum.edge_in_matching)



class GreedyMatchingMaster(aa_pkg.AbstractAlgorithm):
    alg_name = "GreedyParallel"

    def __init__(self, scenario, number_of_processes):
        super().__init__(scenario)

        self.matching_graph = mg_pkg.StatefulMatchingGraph(scenario)
        self.number_of_processes = number_of_processes

        self.task_queue = Queue()
        self.workers = []

        self.result_queues = []
        self.input_queues = []

        for i in range(self.number_of_processes):
            self.result_queues.append(Queue())
            self.input_queues.append(Queue())

        for i in range(self.number_of_processes):
            slave = GreedyMatchingSlave(self.scenario)
            meta_data = WorkerMetaData(greedy_worker_class=slave,
                                       process=None,
                                       task_queue=self.task_queue,
                                       input_queue=self.input_queues[i],
                                       result_queue=self.result_queues[i])
            process = Process(target=slave_execution, args=(meta_data,))
            meta_data.process = process
            self.workers.append(meta_data)
            process.start()


    def _run(self):


        while self.matching_graph.get_size_of_matching() < len(self.matching_graph.communication_pairs):
            #first fill the task queue

            for mb in self.matching_graph.inactive_mbs:
                self.task_queue.put(obj=mb)
            for i in range(self.number_of_processes):
                self.task_queue.put(obj=None)

            for i in range(self.number_of_processes):
                self.workers[i].input_queue.put(self.matching_graph.edge_in_matching)

            best_solution = None
            for i in range(self.number_of_processes):
                active_edges_of_slave = self.workers[i].result_queue.get()
                #print active_edges_of_slave
                #print best_solution
                if active_edges_of_slave is not None and (best_solution is None or len(active_edges_of_slave) > len(best_solution)):
                    best_solution = active_edges_of_slave
                #print best_solution
                #print "\n\n"

            self.matching_graph.reinitialize_from_edges(best_solution)
            print("[{}:{}]: current solution with {} many middleboxes covers {} many cps".format(self.alg_name, self.number_of_processes, self.matching_graph.number_of_active_mbs(), self.matching_graph.get_size_of_matching()))

        for i in range(self.number_of_processes):
            self.workers[i].input_queue.put(obj=None)

        for i in range(self.number_of_processes):
            self.workers[i].process.terminate()

        self.matching_graph.check_validity()
        print("[{}:{}]: found solution with {} many middleboxes!".format(self.alg_name, self.number_of_processes, self.matching_graph.number_of_active_mbs()))

        return self.matching_graph

    def _get_extra_information(self):
        return self.number_of_processes




