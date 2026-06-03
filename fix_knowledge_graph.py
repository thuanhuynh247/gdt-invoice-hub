import json
import os

graph_path = os.path.join(".understand-anything", "knowledge-graph.json")

if not os.path.exists(graph_path):
    print(f"Error: {graph_path} does not exist.")
    exit(1)

with open(graph_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Ensure nodes and edges are lists
if "nodes" not in data or not isinstance(data["nodes"], list):
    data["nodes"] = []
if "edges" not in data or not isinstance(data["edges"], list):
    data["edges"] = []

# Validate and repair nodes
valid_node_types = {
    "file", "function", "class", "module", "concept",
    "config", "document", "service", "table", "endpoint",
    "pipeline", "schema", "resource",
    "domain", "flow", "step",
    "article", "entity", "topic", "claim", "source"
}

NODE_TYPE_ALIASES = {
    "func": "function",
    "fn": "function",
    "method": "function",
    "interface": "class",
    "struct": "class",
    "mod": "module",
    "pkg": "module",
    "package": "module",
    "container": "service",
    "deployment": "service",
    "pod": "service",
    "doc": "document",
    "readme": "document",
    "docs": "document",
    "job": "pipeline",
    "ci": "pipeline",
    "route": "endpoint",
    "api": "endpoint",
    "query": "endpoint",
    "mutation": "endpoint",
    "setting": "config",
    "env": "config",
    "configuration": "config",
    "infra": "resource",
    "infrastructure": "resource",
    "terraform": "resource",
    "migration": "table",
    "database": "table",
    "db": "table",
    "view": "table",
    "proto": "schema",
    "protobuf": "schema",
    "definition": "schema",
    "typedef": "schema",
    "business_domain": "domain",
    "business_flow": "flow",
    "business_process": "flow",
    "task": "step",
    "business_step": "step",
    "note": "article",
    "page": "article",
    "wiki_page": "article",
    "person": "entity",
    "actor": "entity",
    "organization": "entity",
    "tag": "topic",
    "category": "topic",
    "theme": "topic",
    "assertion": "claim",
    "decision": "claim",
    "thesis": "claim",
    "reference": "source",
    "raw": "source",
    "paper": "source",
}

valid_complexities = {"simple", "moderate", "complex"}
complexity_aliases = {
    "low": "simple",
    "easy": "simple",
    "medium": "moderate",
    "intermediate": "moderate",
    "high": "complex",
    "hard": "complex",
    "difficult": "complex"
}

repaired_nodes = []
for idx, node in enumerate(data["nodes"]):
    if not isinstance(node, dict):
        continue
    
    # Check ID
    if "id" not in node:
        node["id"] = f"node_{idx}"
    
    # Clean name
    if "name" not in node or not node["name"]:
        node["name"] = node["id"]
        
    # Clean type
    t = str(node.get("type", "")).lower()
    if t in NODE_TYPE_ALIASES:
        t = NODE_TYPE_ALIASES[t]
    if t not in valid_node_types:
        t = "file"
    node["type"] = t
    
    # Clean complexity
    c = str(node.get("complexity", "")).lower()
    if c in complexity_aliases:
        c = complexity_aliases[c]
    if c not in valid_complexities:
        c = "moderate"
    node["complexity"] = c
    
    # Clean summary
    if "summary" not in node or not node["summary"]:
        node["summary"] = node["name"]
        
    # Clean tags
    if "tags" not in node or not isinstance(node["tags"], list):
        node["tags"] = []
    else:
        node["tags"] = [str(x) for x in node["tags"]]
        
    repaired_nodes.append(node)

data["nodes"] = repaired_nodes

# Validate and repair edges
valid_edge_types = {
  "imports", "exports", "contains", "inherits", "implements",  # Structural
  "calls", "subscribes", "publishes", "middleware",             # Behavioral
  "reads_from", "writes_to", "transforms", "validates",        # Data flow
  "depends_on", "tested_by", "configures",                     # Dependencies
  "related", "similar_to",                                      # Semantic
  "deploys", "serves", "provisions", "triggers",               # Infrastructure
  "migrates", "documents", "routes", "defines_schema",         # Schema/Data
  "contains_flow", "flow_step", "cross_domain",                # Domain
  "cites", "contradicts", "builds_on", "exemplifies", "categorized_under", "authored_by" # Knowledge
}

edge_type_aliases = {
  "extends": "inherits",
  "invokes": "calls",
  "invoke": "calls",
  "uses": "depends_on",
  "requires": "depends_on",
  "relates_to": "related",
  "related_to": "related",
  "similar": "similar_to",
  "import": "imports",
  "export": "exports",
  "contain": "contains",
  "publish": "publishes",
  "subscribe": "subscribes",
  "describes": "documents",
  "documented_by": "documents",
  "creates": "provisions",
  "exposes": "serves",
  "listens": "serves",
  "deploys_to": "deploys",
  "migrates_to": "migrates",
  "routes_to": "routes",
  "triggers_on": "triggers",
  "fires": "triggers",
  "defines": "defines_schema",
  "has_flow": "contains_flow",
  "next_step": "flow_step",
  "interacts_with": "cross_domain",
  "references": "cites",
  "cites_source": "cites",
  "conflicts_with": "contradicts",
  "disagrees_with": "contradicts",
  "refines": "builds_on",
  "elaborates": "builds_on",
  "illustrates": "exemplifies",
  "instance_of": "exemplifies",
  "example_of": "exemplifies",
  "belongs_to": "categorized_under",
  "tagged_with": "categorized_under",
  "written_by": "authored_by",
  "created_by": "authored_by"
}

repaired_edges = []
node_ids = {n["id"] for n in repaired_nodes}

for edge in data["edges"]:
    if not isinstance(edge, dict):
        continue
    if "source" not in edge or "target" not in edge:
        continue
        
    src = edge["source"]
    tgt = edge["target"]
    if src not in node_ids or tgt not in node_ids:
        # Drop dangling edges
        continue
        
    # Clean type
    et = str(edge.get("type", "")).lower()
    if et in edge_type_aliases:
        et = edge_type_aliases[et]
    if et not in valid_edge_types:
        et = "depends_on"
    edge["type"] = et
    
    # Clean direction
    dir_val = str(edge.get("direction", "")).lower()
    if dir_val not in {"forward", "backward", "bidirectional"}:
        dir_val = "forward"
    edge["direction"] = dir_val
    
    # Clean weight
    try:
        w = float(edge.get("weight", 0.5))
    except:
        w = 0.5
    edge["weight"] = max(0.0, min(1.0, w))
    
    repaired_edges.append(edge)

data["edges"] = repaired_edges

# Add required metadata
data["version"] = "1.0.0"
data["project"] = {
    "name": "Webapp XML - GDT Invoice Hub",
    "languages": ["Python", "HTML", "CSS", "JavaScript"],
    "frameworks": ["Flask", "Pytest", "SQLite"],
    "description": "Tax Analytics and Invoice Audit web application supporting corporate tax reconciliation, Foreign Contractor Tax calculations, VAT refunds, aging analysis, and AI compliance auditing.",
    "analyzedAt": "2026-06-03T03:30:00Z",
    "gitCommitHash": "master"
}
data["layers"] = []
data["tour"] = []

with open(graph_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Knowledge graph repaired and metadata added successfully!")
