# -*- coding: utf-8 -*-
with open(r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\templates\result_1_0_new.html', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('<script>') + 8
end = content.find('</script>')
js = content[start:end]

opens = js.count('(')
closes = js.count(')')
brace_open = js.count('{')
brace_close = js.count('}')
bracket_open = js.count('[')
bracket_close = js.count(']')
print(f'Parentheses: ({opens} vs ){closes}')
print(f'Braces: {{{brace_open} vs }}{brace_close}')
print(f'Brackets: [{bracket_open} vs ]{bracket_close}')
print(f'JS total chars: {len(js)}')

idx = js.find('function showTab')
if idx >= 0:
    print(f'showTab found at JS pos: {idx}')
    snippet = js[idx:idx+200]
    print('Snippet:', snippet[:200])
