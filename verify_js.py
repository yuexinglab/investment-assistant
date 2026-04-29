# -*- coding: utf-8 -*-
with open(r'D:\HuaweiMoveData\Users\86136\Documents\GitHub\investment-assistant\templates\result_1_0_new.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the main <script> block (the one without attributes, not the data script)
main_script_idx = content.find('\n<script>')
if main_script_idx == -1:
    main_script_idx = content.find('<script>')
else:
    main_script_idx += 1  # include the newline in the offset

end_script = content.find('</script>', main_script_idx)
js = content[main_script_idx + 8:end_script]

opens = js.count('(')
closes = js.count(')')
brace_open = js.count('{')
brace_close = js.count('}')
bracket_open = js.count('[')
bracket_close = js.count(']')

print('Parentheses: ({0} vs ){1}'.format(opens, closes))
print('Braces: {{{0} vs }}{1}'.format(brace_open, brace_close))
print('Brackets: [{0} vs ]{1}'.format(bracket_open, bracket_close))
print('JS total chars:', len(js))
print()

for fn in ['showTab', 'fillFormWithAnalysis', 'saveComparisonFeedback', 'analyzeFreeNote', 'markDirty']:
    if fn in js:
        print('OK:', fn)
    else:
        print('MISSING:', fn)
