import os
import glob

# Walk the entire directory to fix hardcoded paths
root_dir = "/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"
old_path = "/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"
new_path = "/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"

for subdir, dirs, files in os.walk(root_dir):
    if '.git' in subdir:
        continue
    for file in files:
        if file.endswith(('.sh', '.py', '.md')):
            filepath = os.path.join(subdir, file)
            with open(filepath, 'r') as f:
                try:
                    content = f.read()
                except UnicodeDecodeError:
                    continue
            
            if old_path in content:
                content = content.replace(old_path, new_path)
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Fixed paths in {filepath}")
