from __future__ import annotations
import ast, json, re, sys
from pathlib import Path

CONTROL_CALLS = {
    'Button','Checkbutton','Radiobutton','Label','LabelFrame','Entry','Combobox','Spinbox','Notebook','Treeview'
}
MENU_METHODS = {'add_command','add_checkbutton','add_radiobutton','add_cascade'}


def const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def call_name(fn):
    if isinstance(fn, ast.Name): return fn.id
    if isinstance(fn, ast.Attribute): return fn.attr
    return ''


def kw_str(call, key):
    for kw in call.keywords:
        if kw.arg == key:
            return const_str(kw.value)
    return None


def normalize(s):
    return re.sub(r'\s+', ' ', (s or '').strip())


def main(src_path: str, out_dir: str):
    src = Path(src_path)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding='utf-8-sig')
    tree = ast.parse(text)

    controls=[]; menus=[]; headings=[]; messages=[]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = call_name(node.func)
            if name in CONTROL_CALLS:
                label = kw_str(node, 'text')
                if label:
                    controls.append({'type':name,'text':normalize(label),'line':getattr(node,'lineno',0)})
            if name in MENU_METHODS:
                label = kw_str(node,'label')
                if label:
                    menus.append({'type':name,'text':normalize(label),'line':getattr(node,'lineno',0)})
            if name in {'heading','add'}:
                label = kw_str(node,'text')
                if label:
                    headings.append({'type':name,'text':normalize(label),'line':getattr(node,'lineno',0)})
            if name in {'showinfo','showwarning','showerror','askyesno','askokcancel','askstring'}:
                args=[]
                for a in node.args[:2]:
                    s=const_str(a)
                    if s: args.append(normalize(s))
                if args:
                    messages.append({'type':name,'text':' | '.join(args),'line':getattr(node,'lineno',0)})

    # Also capture literal section names and UI text that appear in constructor arguments.
    literals=[]
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value,str):
            s=normalize(node.value)
            if 2 <= len(s) <= 120 and not s.startswith('__'):
                literals.append(s)

    # Parse current help/tutorial topic ids/titles if present.
    topics=[]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'TUTORIAL_TOPICS':
                    try:
                        value=ast.literal_eval(node.value)
                        for t in value:
                            topics.append({'id':t.get('id',''),'title':t.get('title',''),'keywords':t.get('keywords',''),'body':t.get('body','')})
                    except Exception:
                        pass

    def dedupe(rows):
        seen=set(); out=[]
        for row in sorted(rows,key=lambda r:(r['line'],r['type'],r['text'])):
            key=(row['type'],row['text'])
            if key not in seen:
                seen.add(key); out.append(row)
        return out

    report={
        'source':str(src),
        'controls':dedupe(controls),
        'menus':dedupe(menus),
        'headings':dedupe(headings),
        'messages':dedupe(messages),
        'topic_count':len(topics),
        'topics':topics,
    }
    (out/'ui_feature_inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

    lines=['# AUTOLEDGER UI Feature Inventory','',f"Source: `{src}`",'',f"Help/tutorial topics currently present: **{len(topics)}**",'']
    for title,key in [('Controls','controls'),('Menu items','menus'),('Tabs / headings','headings'),('Dialogs / warnings','messages')]:
        lines += [f'## {title}','']
        for r in report[key]:
            lines.append(f"- `{r['type']}` — **{r['text']}** (line {r['line']})")
        lines.append('')
    lines += ['## Existing Tutorial / Help topics','']
    for t in topics:
        lines.append(f"- `{t['id']}` — **{t['title']}**")
    (out/'ui_feature_inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'reconstructed_r8_core.pyw').write_text(text,encoding='utf-8')
    print(f"Inventory complete: {len(report['controls'])} controls, {len(report['menus'])} menu items, {len(report['headings'])} headings, {len(topics)} topics")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
