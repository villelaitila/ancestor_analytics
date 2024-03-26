import sys

from sgraph import SGraph
from sgraph.converters.graphml import graphml_to_sgraph
from sgraph.converters.graphml import sgraph_to_graphml_file

from verifier import verify_graph


def replace_double_quotes(g):
    # This helps interaction in Softagram Desktop
    stack = [g.rootNode]
    while stack:
        elem = stack.pop(0)
        if '"' in elem.name:
            elem.name = elem.name.replace('"', "")

        if elem.children:
            stack.extend(elem.children)


def convert_from_a_to_b(a, b):
    if 'graphml' in a:
        with open(a) as f:
            s = f.read()
            g = graphml_to_sgraph(s)
            names = []
            for e in g.rootNode.children:
                for n in e.children:
                    print(n.getPath())
                    names.append(n.name)
                names.append(e.name)

            names.sort()
            for n in names:
                print(n)

            # Use only if you need to:
            ## replace_double_quotes(g)

            g.to_xml(fname=b)
    elif 'graphml' in b:
        sgraph_to_graphml_file(SGraph.parse_xml(a), b)
    else:
        raise Exception('Unknown input files, graphml not in ... ' + a + ' ' + b)


if __name__ == '__main__':
    convert_from_a_to_b(sys.argv[1], sys.argv[2])

    graph2 = SGraph.parse_xml(sys.argv[2])
    verify_graph(graph2)
