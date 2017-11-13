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

import logging
log = logging.getLogger(__name__)

import networkx as nx
import sys
import glob
import os
from datamodel import suitable_substrates as ss
from datamodel import substrate


from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # 6367 km is the radius of the Earth
    km = 6367 * c

    latency = km / 200000

    return latency



def performGraphTransformation(G, substrate, graphTransformation):
    for node in G.nodes_iter():
        substrate.add_node(str(node))

    for (tail, head, data) in G.edges_iter(data=True):
        cost = graphTransformation.generateEdgeCost(G, tail, head)
        substrate.add_edge(str(tail), str(head), cost=cost)
        substrate.add_edge(str(head), str(tail), cost=cost)

    return substrate


class SubstrateTransformation_TopologyZoo_Simple:

    def __init__(self):
        pass

    def generateEdgeCost(self, graph, u, v):
        return graph[u][v]['distance']



class TopologyZooReader:

    def __init__(self, path, substrateTransformation):
        self.topologyZooDir = path
        if substrateTransformation is not None:
            self.substrateTransformation = substrateTransformation
        else:
            self.substrateTransformation = SubstrateTransformation_TopologyZoo_Simple()


    def createSummaryOfGraphs(self, minNumberOfNodes = 20, maxNumberOfNodes = 100, enforcePickleUsage=False):
        network_files = glob.glob(self.topologyZooDir + "/"  + "*.gml")

        standard_pop_keys = set(["Country", 'Internal', 'Latitude', 'Longitude', 'id',
            'geocode_country', 'geocode_append', 'geocode_id',   'label'])
        standard_edge_keys = set(["id"])

        networksByFilename = {}

        multipleOccuringNetworks = {}

        for net_file in network_files:
            # Extract name of network from file path
            path, filename = os.path.split(net_file)
            network_name = os.path.splitext(filename)[0]

            graph = self.readGraphRaw(network_name, enforcePickleUsage)

            if graph is None:
                continue

            networksByFilename[network_name] = graph

            nameWithoutDate = ''.join([i for i in network_name if not i.isdigit()])
            dateInformation = ''.join([i for i in network_name if i.isdigit()])

            if nameWithoutDate != network_name and len(dateInformation) >= 4:
                #there is some sort of year inormation included
                if nameWithoutDate not in multipleOccuringNetworks:
                    multipleOccuringNetworks[nameWithoutDate] = []

                multipleOccuringNetworks[nameWithoutDate].append((network_name, dateInformation))

        #select only the most current graphs
        for mNetwork in multipleOccuringNetworks.keys():
            listOfNetworks = multipleOccuringNetworks[mNetwork]
            bestName = None
            bestDate = None
            for network_name, dateInformation in listOfNetworks:
                if len(dateInformation) < 6:
                        dateInformation = dateInformation + "0"*(6-len(dateInformation))
                if bestDate is None or int(dateInformation) > int(bestDate):
                    bestDate = dateInformation
                    bestName = network_name

            for network_name, dateInformation in listOfNetworks:
                if network_name != bestName:
                    print("deleting {} as it is superseded by {}".format(network_name, bestName))
                    del networksByFilename[network_name]

        #order networks according to increasing complexity
        orderedDictOfNetworks = {}
        for network, graph in networksByFilename.items():
            n = graph.number_of_nodes()
            m = graph.number_of_edges()
            if n < minNumberOfNodes or n > maxNumberOfNodes:
                continue
            if n not in orderedDictOfNetworks.keys():
                orderedDictOfNetworks[n] = []
            orderedDictOfNetworks[n].append((network, graph))

        numberOfgraphs = 0
        for numberOfNodes in sorted(orderedDictOfNetworks.keys()):
            print("n = {}: {}".format(numberOfNodes, len(orderedDictOfNetworks[numberOfNodes])))
            numberOfgraphs += len(orderedDictOfNetworks[numberOfNodes])

        print("\n" + "-"*40)
        print("Selected {} graphs.".format(numberOfgraphs))

        print("\nsaving list of selected topologies..\n")


        substrates = ss.SuitableSubstrates()

        for key, value in orderedDictOfNetworks.items():
            for (name, graph) in value:
                new_substrate = substrate.Substrate(name=name)
                performGraphTransformation(G=graph,substrate=new_substrate, graphTransformation=self.substrateTransformation)
                new_substrate.print_it()
                substrates.add_entry(name=name, number_of_nodes=key, substrate=new_substrate)

        ss.pickle_suitable_substrates(substrates)

        substrates = ss.unpickle_suitable_substrates()

        substrates.print_it()

        substrate_names = substrates.get_names()

        example_substrate = substrates.get_substrate(substrate_names[0])

        example_substrate.print_it()

        for substrate_name in substrate_names:
            substrate_graph = substrates.get_substrate(substrate_name)
            if not substrate_graph.check_connectivity():
                print("graph {} is NOT connected!".format(substrate_name))
            else:
                print("graph {} is connected!".format(substrate_name))

        return orderedDictOfNetworks




    def readGraphRaw(self, network_name, enforcePickleUsage = False):
        pickle_file = "{0}/{1}.pickle".format(self.topologyZooDir, network_name)
        log.debug("Looking up {0}..".format(pickle_file))
        graph = None
        if enforcePickleUsage:
            if (os.path.isfile(pickle_file) and
                    (enforcePickleUsage or os.stat(self.topologyZooDir + "/" + network_name + ".gml").st_mtime < os.stat(pickle_file).st_mtime)):
                # Pickle file exists, and source_file is older
                graph = nx.read_gpickle(pickle_file)
                return graph
            else:
                return None
        else:
            if (os.path.isfile(pickle_file) and
                    os.stat(self.topologyZooDir + "/" + network_name + ".gml").st_mtime < os.stat(pickle_file).st_mtime):
                # Pickle file exists, and source_file is older
                graph = nx.read_gpickle(pickle_file)
                return graph
            else:
                graph = nx.read_gml(self.topologyZooDir + "/" + network_name + ".gml")

        if graph.is_multigraph():

            G = nx.Graph()
            for u,v,data in graph.edges_iter(data=True):
                if G.has_edge(u,v):
                    G.edge[u][v]['multiplicity'] += 1
                else:
                    G.add_edge(u, v, multiplicity=1)

            for node, data in graph.nodes_iter(data=True):
                #print data
                if node not in G.nodes():
                    print("pass")
                    continue #I guess we don't need this node then, if it is not connected
                if "Longitude" not in data or "Latitude" not in data:
                    return None
                for key, value in data.items():
                    #print node, " ", key, " ", value
                    G.node[node][key] = value

            #forget about the multigraph and override it by G
            graph = G


        hyperedge_nodes = [ n for n,d in graph.nodes(data=True)
                if d.get("hyperedge")]

        components = sorted(nx.connected_components(graph), key = len, reverse=True)
        #print components

        numberOfNodes = graph.number_of_nodes()
        if len(components) > 1:
            print(network_name, " has ", len(components), " many components")
            for smallerComponents in range(1, len(components)):
                for node in components[smallerComponents]:
                    graph.remove_node(node)
            if graph.number_of_nodes() < numberOfNodes // 2:
                print("discard graph as more than half of the nodes would be excluded")

        nodesWithoutLocation = 0
        for node, data in graph.nodes_iter(data=True):
            if "Longitude" not in data or "Latitude" not in data:
                neighbors = graph.neighbors(node)
                longSum = 0.0
                latSum = 0.0
                for otherNode in neighbors:
                    if "Longitude" not in graph.node[otherNode] or "Latitude" not in graph.node[otherNode]:
                        nodesWithoutLocation += 1
                    else:
                        longSum += graph.node[otherNode]["Longitude"]
                        latSum += graph.node[otherNode]["Latitude"]
                if nodesWithoutLocation > 0:
                    print("discard ", network_name, " as ", nodesWithoutLocation, " of ", graph.number_of_nodes(), " many nodes do not contain location information")
                    return None
                longSum = longSum / len(neighbors)
                latSum = latSum / len(neighbors)
                graph.node[node]["Longitude"] = longSum
                graph.node[node]["Latitude"] = latSum


        for u,v, data in graph.edges_iter(data=True):
            #print graph.node[u]
            #print graph.node[v]
            #print ">>", u, " ", v
            graph.edge[u][v]['distance'] = haversine(graph.node[u]["Longitude"], graph.node[u]["Latitude"], graph.node[v]["Longitude"], graph.node[v]["Latitude"])

        graph = graph.to_undirected()
        nx.write_gpickle(graph, pickle_file)
        return graph


    def readSubstrate(self, filename, substrateTransformationOverwrite = None):
        G = self.readGraphRaw(filename)
        new_substrate = substrate.Substrate(filename)
        if substrateTransformationOverwrite is None:
            performGraphTransformation(G, new_substrate, self.substrateTransformation)
        else:
            performGraphTransformation(G, new_substrate, substrateTransformationOverwrite)
        return new_substrate

#    def drawGraph(self, network_name):
#        graph = self.readGraphRaw(network_name)
#        pos = {}
#        for node in graph.nodes_iter():
#            pos[node] = (graph.node[node]["Longitude"],graph.node[node]["Latitude"])
#        nx.draw(graph, pos)
#        plt.show()



class SubstrateTransformation_IGen:

    def __init__(self, popNodeCapacity, nonPopNodeCapacity, bbEdgeCapacity, nonBbEdgeCapacity):
        self.popNodeCapacity = popNodeCapacity
        self.nonPopNodeCapacity = nonPopNodeCapacity
        self.bbEdgeCapacity = bbEdgeCapacity
        self.nonBbEdgeCapacity = nonBbEdgeCapacity

    def generateNodeCapacity(self, graph, node):
        pop = False
        for (tail, head, data) in graph.edges_iter(node, data=True):
            if data['bandwidth'] > 155000000:
                pop = True
        if pop:
            return self.popNodeCapacity
        else:
            return self.nonPopNodeCapacity

    def generateEdgeCapacity(self, graph, u, v):
        if graph[u][v]['bandwidth'] > 155000000:
            return self.bbEdgeCapacity
        else:
            return self.nonBbEdgeCapacity

    def generateNodeCost(self, graph, u):
        return 1.0

    def generateEdgeCost(self, graph, u, v):
        return 1.0



def main(argv):
    foo = TopologyZooReader(argv[0], SubstrateTransformation_TopologyZoo_Simple())
    print(foo.createSummaryOfGraphs())


if __name__ == '__main__':
    main(sys.argv[1:])


