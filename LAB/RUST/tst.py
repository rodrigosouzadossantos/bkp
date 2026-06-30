import nautilus

data = nautilus.list_bucket_parallel(
    'analise-dados',
    '' #'projeto-ia-submarina/ia-frente-ambiental',
  )

from collections import defaultdict

def build_tree(paths):
    tree = lambda: defaultdict(tree)
    root = tree()

    for path in paths:
        parts = path.strip("/").split("/")
        node = root
        for part in parts:
            node = node[part]

    return root

def print_tree(node, indent=0):
    for name, child in node.items():
        print("  " * indent + name)
        print_tree(child, indent + 1)

# achata todos os arquivos
all_files = [
    f for files in data.values() for f in files
]

tree = build_tree(all_files)
print_tree(tree)
