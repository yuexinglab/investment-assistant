# -*- coding: utf-8 -*-
import subprocess

result = subprocess.run(
    ['curl', '-s', 'http://127.0.0.1:5000/project/A1_%E9%87%8D%E6%B5%8B_20260429_141115/result_new'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
content = result.stdout

# Check lines around the problematic area
lines = content.split('\n')
for i in range(1985, 2000):
    if i < len(lines):
        print(f'{i+1}: {repr(lines[i][:200])}')

# Also verify showTab is still present
print('\n---')
print('showTab in response:', 'function showTab' in content)

# Check for the fixed step1 lines
for i, line in enumerate(lines):
    if 'step1' in line and 'const aiOutputs' not in line and 'step1:' in line:
        print(f'Line {i+1}: {repr(line[:200])}')
