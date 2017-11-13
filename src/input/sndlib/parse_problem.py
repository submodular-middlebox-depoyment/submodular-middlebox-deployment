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


if __name__ == "__main__":
    model, graph = parse_problem("./problems/model.xml", "./instances-xml/abilene/abilene.xml")
    print("Obtained {}".format(model))
    print("\nNode coordinates type: ", graph.graph["coordinatesType"])
    print("\nNodes:")
    print("\n\t" + "\n\t".join("{} {}".format(id, a["position"]) for id, a in graph.nodes(data=True)))
    print("\nLinks:")
    print("\n\t" + "\n\t".join("{} {} {}".format(s, t, a["attributes"]) for s, t, a in graph.edges(data=True)))
    print("\nDemands:")
    print("\n\t" + "\n\t".join(str(d) for d in graph.graph["demands"]))
