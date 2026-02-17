"""Fix UUID converter conflict in conftest.py"""
with open('tests/conftest.py', 'r') as f:
    lines = f.readlines()

# Find the end of the docstring and add UUID fix after it
new_lines = []
docstring_ended = False
for i, line in enumerate(lines):
    new_lines.append(line)
    if not docstring_ended and line.strip() == '"""':
        docstring_ended = True
        # Add UUID fix after docstring
        new_lines.append('\n')
        new_lines.append('# VIBE COMPLIANT: Prevent Django Ninja UUID converter conflict\n')
        new_lines.append('import os\n')
        new_lines.append('os.environ["DJANGO_NINJA_SKIP_UUID_CONVERTER"] = "true"\n')
        new_lines.append('\n')

with open('tests/conftest.py', 'w') as f:
    f.writelines(new_lines)

print('Successfully added UUID conflict resolution')