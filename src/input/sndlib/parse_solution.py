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
from .parse_problem import read_xml_file, get_text_attribute, get_text_attributes_as_list

Solution = namedtuple("Solution", "linkConfigurations demandRoutings")

LinkConfiguration = namedtuple("LinkConfiguration", "id installedModules")
InstalledModule = namedtuple("InstalledModule", "capacity installCount")

DemandRouting = namedtuple("DemandRouting", "demandID flowPaths")
FlowPath = namedtuple("FlowPath", "flowPathValue routingPath")


def parse_solution_file(path_to_solution_xml):
    root_element = read_xml_file(path_to_solution_xml)
    link_configurations_element = root_element.find("linkConfigurations")
    link_configurations = _get_link_configurations(link_configurations_element)

    demand_routings_elements = root_element.findall("demandRoutings")
    demand_routings = {elem.attrib["state"]: _get_demand_routings(elem) for elem in demand_routings_elements}
    return Solution(link_configurations, demand_routings)


def _get_link_configurations(link_configurations_element):
    if link_configurations_element is None:
        return None
    link_configurations = link_configurations_element.findall("linkConfiguration")
    result = []
    for link_config_element in link_configurations:
        link_id = link_config_element.attrib["linkId"]
        modules = []
        for module_element in link_config_element.findall("installedModule"):
            cap = get_text_attribute(module_element, "capacity", float)
            install_count = get_text_attribute(module_element, "installCount", float)
            modules.append(InstalledModule(cap, install_count))
        result.append(LinkConfiguration(link_id, modules))
    return result


def _get_demand_routings(demand_routings_xml_element):
    return [_get_single_demand_routing(elem) for elem in demand_routings_xml_element.findall("demandRouting")]


def _get_single_demand_routing(demand_routing_xml_element):
    demand_id = demand_routing_xml_element.attrib["demandId"]
    list_of_flow_path_elements = demand_routing_xml_element.findall("flowPath")
    flow_paths = _get_flow_paths(list_of_flow_path_elements)
    return DemandRouting(demand_id, flow_paths)


def _get_flow_paths(list_of_flow_path_elements):
    result = []
    for flow_path_elem in list_of_flow_path_elements:
        value = get_text_attribute(flow_path_elem, "flowPathValue", float)
        routing_path = get_text_attributes_as_list(flow_path_elem.find("routingPath"), "linkId")
        result.append(FlowPath(value, routing_path))
    return result


if __name__ == "__main__":
    solution = parse_solution_file("./solutions/solution.xml")
    print("\nLink Configurations:\n")
    for lc in solution.linkConfigurations:
        print("\t", lc)
    print("\nDemand Routings:\n")
    for state, routing_list in solution.demandRoutings.items():
        print("\t", state)
        for routing in routing_list:
            print("\t\t", routing)
