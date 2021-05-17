import requests
import pyewts
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
EWTSCONV = pyewts.pyewts()


def ewtstobo(ewtsstr):
    res = EWTSCONV.toUnicode(ewtsstr)
    return res

def get_id(URI):    
    return URI.split("/")[-1]

def get_author_id(g, work_id):
    work_id = f"M{work_id}"
    instance_ids = g.objects(BDR[work_id], BDO["instanceOf"])
    for instance_id in instance_ids:
        instance_id = get_id(str(instance_id))
    agent_ids = g.objects(BDR[instance_id], BDO["creator"])
    for agent_id in agent_ids:
        agent_id = get_id(str(agent_id))
    author_ids = g.objects(BDR[agent_id], BDO["agent"])
    for author_id in author_ids:
        author_id = get_id(str(author_id))
    return author_id

def parse_author_ttl(author_ttl, work_id):
    g = Graph()
    try:
        g.parse(data=author_ttl, format="ttl")
    except:
        print(f"{work_id}.ttl Contains bad syntax")
        return {}
    author_id = get_author_id(g, work_id)
    author = g.value(BDR[author_id], SKOS["prefLabel"])
    author = ewtstobo(author)
    print(author)
    return author
   
def get_author_ttl(work_id):
    try:
        author_ttl = requests.get(f"http://purl.bdrc.io/query/graph/OP_info?R_RES=bdr:{work_id}&format=ttl")
        print(author_ttl.text)
        return author_ttl.text
    except:
        print(' TTL not Found!!!')
        return None


if __name__=="__main__":
    work_id = "W1KG17431"
    author_ttl = get_author_ttl(work_id)
    author = parse_author_ttl(author_ttl, work_id)
    print(author)