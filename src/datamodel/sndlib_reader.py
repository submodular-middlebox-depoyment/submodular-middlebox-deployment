# MIT License
#
# Copyright (c) 2017 Matthias Rost, Alexander Elvers, Elias Döhne
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

__author__ = "Matthias Rost, Alexander Elvers, Elias Döhne (mrost / aelvers / edoehne <AT> inet.tu-berlin.de)"

import networkx as nx
from xml.etree import ElementTree
import re
from collections import namedtuple
import os
import math
import pickle
import random

from algorithms import optimal_mip_diff_weights as mip_pkg, greedy_diff_weights
from algorithms import greedy_diff_weights as greedy_diff_weights_pkg

from datamodel import requests  as req_pkg
from datamodel import substrate as sub_pkg
from datamodel import scenario  as scen_pkg
from datamodel import substrate_reader as sub_reader_pkg
from util import util as util_pkg


VALID_MODEL_PARAMETERS = {
    "demandModel": ["UNDIRECTED", "DIRECTED"],
    "linkModel": ["UNDIRECTED", "BIDIRECTED", "DIRECTED"],
    "linkCapacityModel": ["LINEAR_LINK_CAPACITIES", "SINGLE_MODULAR_CAPACITIES", "MODULAR_LINK_CAPACITIES", "EXPLICIT_LINK_CAPACITIES"],
    "fixedChargeModel": ["YES", "NO"],
    "routingModel": ["CONTINUOUS", "INTEGER", "SINGLE_PATH", "OSPF_SINGLE_PATH", "OSPF_EQUAL_SPLIT_PATH"],
    "admissiblePathModel": ["ALL_PATHS", "EXPLICIT_LIST"],
    "hopLimitModel": ["INDIVIDUAL_HOP_LIMITS", "IGNORE_HOP_LIMITS"],
    "objectiveModel": ["MINIMIZE_TOTAL_COST"],
    "survivabilityModel": ["NO_SURVIVABILITY", "ONE_PLUS_ONE_PROTECTION", "SHARED_PATH_PROTECTION", "UNRESTRICTED_FLOW_RECONFIGURATION"],
    "nodeModel": ["NODE_HARDWARE", "NO_NODE_HARDWARE"]
}

Model = namedtuple("Model", "nodeModel linkModel linkCapacityModel fixedChargeModel demandModel routingModel admissiblePathModel hopLimitModel objectiveModel survivabilityModel")
LinkAttributes = namedtuple("LinkAttributes", "id routingCost setupCost preInstalledModule additionalModules")
LinkModule = namedtuple("LinkModule", "capacity cost")
Demand = namedtuple("Demand", "id source target demandValue admissiblePaths")


def read_xml_file(path):
    with open(path, "r") as f:
        xml_string = f.read()
    # remove the xml namespace for convenience:
    xml_string = re.sub(' xmlns="[^"]+"', '', xml_string, count=1)
    return ElementTree.fromstring(xml_string)


def parse_problem(path_to_model_xml, path_to_network_xml):
    model_root = read_xml_file(path_to_model_xml)
    model = _extract_model(model_root)

    network_root = read_xml_file(path_to_network_xml)
    network_structure_element = network_root.find("networkStructure")

    graph = _extract_network_structure(network_structure_element)

    network_demands_element = network_root.find("demands")
    demands = None
    if network_demands_element is not None:
        demands = _extract_demands(network_demands_element)
    graph.graph["demands"] = demands
    return model, graph


def _extract_model(root):
    attribute_dict = dict()
    for attribute in Model._fields:
        value = root.find(attribute).text
        # Sanity Check:
        if value not in VALID_MODEL_PARAMETERS[attribute]:
            raise Exception("{} is not a valid value for model attribute {}".format(value, attribute))
        attribute_dict[attribute] = value
    return Model(**attribute_dict)  # convert the dict to the namedtuple defined above


def _extract_network_structure(root):
    graph = nx.Graph()
    nodes_element = root.find("nodes")
    coordinate_type = nodes_element.get("coordinatesType", None)
    nodes = nodes_element.findall("node")

    graph.graph["coordinatesType"] = coordinate_type
    for node_element in nodes:
        _add_node_to(graph, node_element)
    links = root.find("links").findall("link")
    for link_element in links:
        _add_edge_to(graph, link_element)
    return graph


def _add_node_to(graph, node_element):
    node_id = node_element.attrib["id"]
    node_coordinate_element = node_element.find("coordinates")
    node_x = float(node_coordinate_element.find("x").text)
    node_y = float(node_coordinate_element.find("y").text)
    graph.add_node(node_id, position=(node_x, node_y))


def _add_edge_to(graph, link_element):
    source = link_element.find("source").text
    target = link_element.find("target").text
    attributes = _get_link_attributes(link_element)
    graph.add_edge(source, target, attributes=attributes)


def _get_link_attributes(link_element):
    link_id = link_element.attrib["id"]
    routing_cost = get_text_attribute(link_element, "routingCost", float)
    setup_cost = get_text_attribute(link_element, "setupCost", float)
    preinstalled_module = _build_link_module(link_element.find("preInstalledModule"))

    additional_modules_element = link_element.find("additionalModules")
    additional_modules = None
    if additional_modules_element is not None:
        additional_modules = additional_modules_element.findall("addModule")
        additional_modules = [_build_link_module(lm_element) for lm_element in additional_modules]
    return LinkAttributes(link_id, routing_cost, setup_cost, preinstalled_module, additional_modules)


def _build_link_module(link_module_element):
    if link_module_element is None:
        return None
    cap = float(link_module_element.find("capacity").text)
    cost = float(link_module_element.find("cost").text)
    return LinkModule(cap, cost)


def _extract_demands(demands_element):
    return [_build_demand_object(d) for d in demands_element.findall("demand")]


def _build_demand_object(demand_element):
    source = demand_element.find("source").text
    target = demand_element.find("target").text
    demand_id = demand_element.attrib["id"]
    demand_value = get_text_attribute(demand_element, "demandValue", float)
    admissible_paths_element = demand_element.find("admissiblePaths")
    admissible_paths = None
    if admissible_paths_element is not None:
        admissible_paths = dict()
        for elem in admissible_paths_element.findall("admissiblePath"):
            if elem is None:
                continue
            id = elem.attrib["id"]
            admissible_paths[id] = [link_id.text for link_id in elem.findall("linkId")]
    return Demand(demand_id, source, target, demand_value, admissible_paths)


def get_text_attribute(element, attribute_name, transformation=lambda x: x):
    child = element.find(attribute_name)
    if child is not None:
        return transformation(child.text)


def get_text_attributes_as_list(element, attribute_name, transformation=lambda x: x):
    child_list = element.findall(attribute_name)
    if child_list is not None:
        return [transformation(c.text) for c in child_list]


class SNDTopologyInfo:

    def __init__(self, name, graph):
        self.name = name
        self.graph = graph
        self.number_nodes = len(graph.nodes())
        self.number_edges = len(graph.edges())
        self.number_demands = len(graph.graph["demands"])


    def __str__(self):
        return "Name: {0:<14}\t|V|: {1:>4}\t|E|: {2:>4}\t|D|: {3:>5}".format(self.name, self.number_nodes, self.number_edges, self.number_demands)



selected = ["ta2", "zib54", "germany50", "pioro40", "nobel-eu"]


def euclid_distance(x_1,y_1,x_2,y_2):
    result = math.pow(x_1-x_2,2)
    result += math.pow(y_1-y_2,2)
    return math.sqrt(result)

def create_scenario_from_sndlib_instance(sndlib_instance_name):
    model, graph = parse_problem("./input/sndlib/problems/model.xml", "./input/sndlib/instances-xml/{0}/{0}.xml".format(sndlib_instance_name))

    substrate = sub_pkg.Substrate(sndlib_instance_name)

    node_coordinates = {}

    for node in graph.nodes():
        substrate.add_node(node)
        node_coordinates[node] = graph.node[node]["position"]
    for edge in graph.edges():
        u,v = edge
        long_u, lat_u = node_coordinates[u]
        long_v, lat_v = node_coordinates[v]
        edge_costs = None
        print(graph.graph["coordinatesType"])
        if graph.graph["coordinatesType"] == "pixel":
            edge_costs = euclid_distance(long_u, lat_u, long_v, lat_v)
        elif graph.graph["coordinatesType"] == "geographical":
            edge_costs = sub_reader_pkg.haversine(long_u, lat_u, long_v, lat_v)
        else:
            raise Exception("Unknown!")

        print("costs {} for |({},{})-({},{})|".format(edge_costs, long_u, lat_u, long_v, lat_v))
        substrate.add_edge(u,v,cost=edge_costs)
        substrate.add_edge(v,u,cost=edge_costs)

    cum_demand = 0
    requests = []
    for demand in graph.graph["demands"]:
        id, source, target, demand, _ = demand
        print("{} {} {} {}".format(id, source, target, demand))
        requests.append(req_pkg.Request(source, target, capacity=demand, max_deviation=0.0))
        cum_demand += demand

    mbs = {}
    for node in substrate.get_nodes():
        mbs[node] = 4 * cum_demand / len(graph.nodes())

    scen = scen_pkg.Scenario(sndlib_instance_name + "_prototype", substrate, requests, mbs)

    return scen


def generate_overview():
    topos = []
    for file in os.listdir("./input/sndlib/instances-xml/"):
        #if file in selected:
        model, graph = parse_problem("./input/sndlib/problems/model.xml", "./input/sndlib/instances-xml/{0}/{0}.xml".format(file))
        topos.append(SNDTopologyInfo(file, graph))

    topos_sorted = sorted(topos, key= lambda x: -x.number_nodes)
    for topo in topos_sorted:
        print(topo)
    for topo in topos_sorted:
        print(topo.graph)

def try_algorithms():


    import os

    filename = "sndlib.cpickle"

    scen = None
    if os.path.exists(filename):
        with open(filename) as f:
            scen = pickle.loads(f.read())
    else:
        scen = create_scenario_from_sndlib_instance("nobel-eu")
        with open(filename, "w") as f:
            f.write(pickle.dumps(scen))

    #mc = mip_pkg.ExactDeploymentMIP_diff_weights(scen, mip_gap=0.001)
    #mc.run()

    for dev in [i/10 for i in range(20)]:
        for repetition in range(25):
            print("\n\n\n\n\nSTARTING \tdev: {}\trep: {}\n\n\n\n\n".format(dev, repetition))
            requests = []
            for request in scen.requests:
                if random.random() < 0.5:
                    requests.append(request)
                    request.max_deviation = dev
            demand = sum([request.capacity for request in requests])
            middleboxes = dict(scen.middleboxes)

            for mb in middleboxes.keys():
                middleboxes[mb] = 4 * demand / len(scen.middleboxes.keys())

            scenario = scen_pkg.Scenario(id=scen.id, substrate=scen.substrate, requests=requests, middleboxes=middleboxes)



            alg = greedy_diff_weights_pkg.Greedy_diff_weights(scenario)
            result = alg.run()

            mip = mip_pkg.ExactDeploymentMIP_diff_weights(scenario=scenario)
            result_mip = mip.run()

            if len(result.active_mbs) > len(result_mip.active_mbs):
                raise Exception("More costly solution found!")






if __name__ == "__main__":
    #generate_overview()
    #lala = create_scenario_from_sndlib_instance("pioro40")
    try_algorithms()




