#! /usr/bin/env python

import networkx as nx

import os
import glob
import sys
from time import strftime
import numpy as np
import matplotlib.pyplot as plt

import optparse

import pprint

def category_counts(data):
    keys = set(data)
    for key in sorted(keys):
        print("{0}\t{1}".format(key.ljust(10), data.count(key)))
    print("{0}\t{1}".format("Total".ljust(10), len(data)))


def main():
    opt = optparse.OptionParser()
    opt.add_option('--file', '-f', help="Load data from FILE")
    opt.add_option('--directory', '-d', help="process directory")
    opt.add_option('--output_dir', '-o', help="process directory")
    options = opt.parse_args()[0]

    network_files = []
    if options.file:
        network_files.append(options.file)

    if options.directory:
        network_files = glob.glob(options.directory + "*.gml")

    if len(network_files) == 0:
        print("No files found. Please specify -f file or -d directory")
        sys.exit(0)

    if options.directory:
        path = options.directory
    elif options.file:
        path, filename = os.path.split(options.file)

    pickle_dir = path + "/cache"
    if not os.path.isdir(pickle_dir):
        os.mkdir(pickle_dir)

    summary_data = {}
    stats = {}

    disconnected_networks = {}
    multi_edge_count = 0
    pop_data_count = 0
    edge_data_count = 0
    standard_pop_keys = set(["Country", 'Internal', 'Latitude', 'Longitude', 'id',
        'geocode_country', 'geocode_append', 'geocode_id',   'label'])
    standard_edge_keys = set(["id"])
    geocode_ratio = dict()
    nice_scenarios = []
    nice_summary = {}

    for net_file in network_files:

        # Extract name of network from file path
        path, filename = os.path.split(net_file)
        network_name = os.path.splitext(filename)[0]
        stats[network_name] = {}

        #print "Converting: {0}".format(network_name)

        #if network_files.index(net_file) > 20:
        #    break

        pickle_file = "{0}/{1}.pickle".format(pickle_dir, network_name)
        if (os.path.isfile(pickle_file) and
            os.stat(net_file).st_mtime < os.stat(pickle_file).st_mtime):
            # Pickle file exists, and source_file is older
            graph = nx.read_gpickle(pickle_file)
        else:
            print("Caching copy of %s" % network_name)
            # No pickle file, or is outdated
            graph = nx.read_gml(net_file)
            nx.write_gpickle(graph, pickle_file)

        graph = graph.to_undirected()
        if graph.is_multigraph():
            multi_edge_count += 1
        graph = nx.MultiGraph(graph)
        #print "Network", graph.graph.get("Network")

        external_nodes = [ n for n in graph.nodes()
                          if 'Internal' in graph.node[n] and
                          graph.node[n]['Internal'] == 0]
        graph.remove_nodes_from(external_nodes)
        hyperedge_nodes = [ n for n,d in graph.nodes(data=True)
                if d.get("hyperedge")]
        stats[network_name]['hyperedge'] = len(hyperedge_nodes)
        stats[network_name]['external'] = len(external_nodes)

        for node, data in graph.nodes(data=True):
            if any(key for key in data if key not in standard_pop_keys):
                #print "node data for", data
                pop_data_count += 1
                break

        nonStandardKeys = set()
        for s, t, data in graph.edges(data=True):
            if any(key for key in data if key not in standard_edge_keys):
                foobar = [key for key in data if key not in standard_edge_keys]
                #print foobar
                nonStandardKeys = nonStandardKeys.union(set([key for key in data if (key not in standard_edge_keys and key not in nonStandardKeys)]))
                #print "edge data for", data
                edge_data_count += 1
                #break
        numberOfSpeeds = 0.1
        if 'LinkSpeedRaw' in nonStandardKeys:
             print("nonStandardKeys ", nonStandardKeys)
             linkSpeeds = set([data['LinkSpeedRaw'] for s, t, data in graph.edges(data=True) if 'LinkSpeedRaw' in data])
             if len(linkSpeeds) > 1:
                 print(linkSpeeds)
                 nice_scenarios.append((net_file, len(graph.nodes()), len(graph.edges()), linkSpeeds))
             numberOfSpeeds = len(linkSpeeds)
        nice_summary[net_file[3:]] = (len(graph.nodes()), len(graph.edges()), numberOfSpeeds)


        geocoded_nodes = sum(1 for n, d in graph.nodes(data=True)
                if d.get("Latitude") and d.get("Longitude"))
        geocode_ratio[network_name] = geocoded_nodes/len(graph)

        if not nx.is_connected(graph):
            components = [component for component in
                          nx.connected_components(graph)]
            component_sizes = []
            for component in components:
                # Only want internal, non hyperedge nodes
                component_size = len([n for n in component
                                      if (n not in external_nodes
                                          and n not in hyperedge_nodes)])
                component_sizes.append(component_size)

            disconnected_networks[network_name] = component_sizes

        summary_data[network_name] = {}

        for key, val in graph.graph.items():
            # And also store in html data
            summary_data[network_name][key] = val

    # And range
    print("------")
    print("%i networks" % len(summary_data))
    unique_networks = set(d.get("Network") for n, d in summary_data.items())
    print("Unique:", len(unique_networks))
    print("Multi-edges", multi_edge_count)
    print("Networks with pop metadata", pop_data_count)
    print("Networks with edge metadata", edge_data_count)
    print("Geocode ratio > 10%", sum(1 for key, val in geocode_ratio.items() if val > 0.1))
    print("Geocode ratio > 50%", sum(1 for key, val in geocode_ratio.items() if val > 0.5))
    print("Geocode ratio > 90%", sum(1 for key, val in geocode_ratio.items() if val > 0.9))
    print("Geocode ratio > 95%", sum(1 for key, val in geocode_ratio.items() if val > 0.95))


# stats
    print("-----")
    print("Hyperedges")
    print("Count:", sum(1 for n, d in stats.items() if d.get('hyperedge')))
    """
    for network, data in sorted(stats.items()):
        if data['hyperedge']:
            print network, "\t\t", data['hyperedge']
            """

    print("-----")
    print("External Nodes")
    print("Count:", sum(1 for n, d in stats.items() if d.get('external')))
    """
    for network, data in sorted(stats.items()):
        if data['external']:
            print network, "\t\t", data['external']
    """


    # And range
    print("------")
    types_keys = ['Access', 'Backbone', 'Customer', 'Testbed', 'Transit', 'IX']
    print("Type".ljust(10) + "\tCOM\tREN\tTotal")
    for key in types_keys:
        # All networks that have this statistic
        all_nets = [network for network, data in summary_data.items() if
                    key in data and data[key] == 1]
        # Commercial subset
        com_nets = [network for network in all_nets
               if summary_data[network]['Type'] == 'COM']
        # Research subset
        ren_nets = [network for network in all_nets
               if summary_data[network]['Type'] == 'REN']

        print("{0}\t{1}\t{2}\t{3}".format(key.ljust(10), len(com_nets),
                                          len(ren_nets), len(all_nets)))

    # And range
    print("------")
    print("Range: ")
    all_vals = [d["GeoExtent"] for d in summary_data.values()]
    category_counts(all_vals)

    print("-----")
    print("Connected Components:")
    print("Network".ljust(10) + "\tConnected Components")
    for key, val in sorted(disconnected_networks.items()):
        print("%s\t%s" % (key.ljust(10), "/".join([str(v) for v in val])))

    # Layer
    print("----------")
    print("Layer:")
    all_vals = [d["Layer"] for d in summary_data.values()]
    category_counts(all_vals)

    #print "No layer: " + ",".join([network for network, data
    #                               in summary_data.items()
    #                               if data["Layer"] ==s ""])

    # Com and Ren
    print("----------")
    print("Type:")
    all_vals = [d["Type"] for d in summary_data.values()]
    category_counts(all_vals)


    print("----------")
    print("Provenance:")
    all_vals = [d["Provenance"] for d in summary_data.values()]
    category_counts(all_vals)

    # and dates
    print("----------")
    print("Date:")
    # We need to look at current/historical/dynamic in conjunction with the date
    all_dates = []
    # The value depends on the DateType field. Historical and current networks
    # are classified by year. Dynamic networks are kept as dynamic.
    all_dates += [data['NetworkDate'] for data in summary_data.values()
                  if data.get('DateType') == "Historic"]
    #all_dates += [data['NetworkDate'] for data in summary_data.values()
    #              if data['DateType'] == "Current"]
    all_dates += ['Current' for data in summary_data.values()
                  if data.get('DateType') == "Current"]

    current_nets = [network for network, data in summary_data.items()
                  if data.get('DateType') == "Current"]
    #for net in current_nets:
    #    print ("%s %s" % (net, summary_data[net]['DateObtained']))
    # Truncate date from YYYY-MM to just YYYY
    # Get list of dates first, then iterate using it (don't want to modify list
    # while iterating over it)
    yyyy_mm = [date for date in all_dates if len(date) == 7 and date[4] == "-"
               and date[:4].isdigit()]
    for date in yyyy_mm:
        all_dates.remove(date)
        all_dates.append(date[:4])

    #all_dates = [date.split("-")[0] for date in all_dates
    #             if len(date) == 7 and date[5] == "-"]
    # Dynamic networks remain as dynamic
    all_dates += ['Dynamic' for data in summary_data.values()
                  if data.get('DateType') == "Dynamic"]
    #category_counts(all_dates)

    """
    histogram = []
    numeric_dates = [int(date) for date in all_dates if date.isdigit()]
    bins = [min(numeric_dates), 2000, 2005, 2010]
    for date in numeric_dates:
        for bin in bins:
            if date <= bin:
                histogram[bin]
    """
    pp = pprint.PrettyPrinter(indent=2, width=240)
    pp.pprint(nice_scenarios)
    nice_dict = {a[3:] : [b,c,d] for (a,b,c,d) in nice_scenarios}
    for a in sorted(nice_dict.keys()):
        pp.pprint([a, nice_dict[a]])

    colors = np.random.rand(len(nice_summary.keys()))

    x = [nice_summary[key][0] for key in sorted(nice_summary.keys())]
    y = [nice_summary[key][1] for key in sorted(nice_summary.keys())]
    area = 50#[150 * nice_summary[key][2] for key in sorted(nice_summary.keys())]

    fig = plt.figure()
    ax = plt.gca()
    plt.scatter(x, y, s=area, c=colors, alpha=0.5)
#    plt.semilogy(x, y, c=colors, alpha=0.5)
#    ax.set_yscale('semilog')
    ax.set_xscale('log')
    #ax.set_yscale('log')
    plt.xlim(8,100)
    plt.ylim(1,120)
    plt.title("Topology Zoo Overview")
    plt.xlabel("number of nodes (log)")
    plt.ylabel("number of edges ")
    ax.grid(True)
    ax.set_xticks([10 * i for i in range(1,11)])
    ax.set_xticklabels([10 * i for i in range(1,11)])
    plt.show()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
