import re

def generate_dot_file():
    with open('module/ui/page.py', 'r') as f:
        content = f.read()

    # Find all page definitions that are not commented out
    pages = re.findall(r'^\s*(\w+)\s*=\s*Page\(', content, re.MULTILINE)
    unique_pages = sorted(list(set(pages)))

    # Find all links that are not commented out
    links = re.findall(r'^\s*(\w+)\.link\(.*?destination=(\w+)\)', content, re.MULTILINE)

    with open('state_machine.dot', 'w') as f:
        f.write('digraph G {\n')
        f.write('  rankdir="LR";\n')
        f.write('  node [shape=box, style=rounded];\n')

        # Add nodes to the graph
        for page in unique_pages:
            f.write(f'  "{page}";\n')

        # Add edges to the graph
        for source, destination in links:
            if source in unique_pages and destination in unique_pages:
                f.write(f'  "{source}" -> "{destination}";\n')

        f.write('}\n')

if __name__ == '__main__':
    generate_dot_file()
    print("state_machine.dot file generated successfully.")
