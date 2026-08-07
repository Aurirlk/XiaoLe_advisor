"""
Robust .js → .vue SFC converter.
Restores components from git then converts to Vite-compatible .vue files.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "temp_components"
DST = ROOT / "frontend" / "src" / "components"

def find_template_end(content, start):
    """Find closing backtick of template string. Simple bracket-aware search."""
    i = start
    while i < len(content):
        if content[i] == '`' and (i == 0 or content[i-1] != '\\'):
            after = content[i+1:].lstrip()
            if not after or after[0] == ',' or after[0] == '\n' or \
               after.startswith('data(') or after.startswith('computed') or \
               after.startswith('methods') or after.startswith('props') or \
               after.startswith('emits') or after.startswith('watch') or \
               after.startswith('components') or after.startswith('mounted') or \
               after.startswith('before') or after.startswith('created'):
                return i
        i += 1
    return -1

def convert_file(js_path, vue_path):
    content = js_path.read_text(encoding='utf-8')
    
    # Extract imports (keep top-level)
    imports = []
    has_const_decl = False
    const_name = ''
    
    for line in content.split('\n'):
        s = line.strip()
        if s.startswith('import '):
            imports.append(line)
    
    # Find template start
    m = re.search(r'\btemplate:\s*`', content)
    if not m:
        print(f"  SKIP {js_path.name}: no template")
        return False
    
    template_start = m.end()
    template_end = find_template_end(content, template_start)
    
    if template_end < 0:
        print(f"  SKIP {js_path.name}: can't find template end")
        return False
    
    template = content[template_start:template_end]
    
    # Build script: everything except template: `...`
    before = content[:m.start()]
    after = content[template_end+1:]
    
    # Handle the comma after template backtick
    after = re.sub(r'^\s*,?\s*', '\n', after)
    
    script = before + after
    
    # Fix imports for sibling path (src/components/)
    script = re.sub(r"from\s+['\"]\.\.\/utils\/([^'\"]+)\.js", r"from '../../utils/\1.js'", script)
    script = re.sub(r"from\s+['\"]\.\/core\/([^'\"]+)\.js", r"from './core/\1.vue'", script)
    script = re.sub(r"from\s+['\"]\.\/((?!core/)[^/][^'\"]*)\.js", r"from './\1.vue'", script)
    script = re.sub(r"from\s+['\"]\.\/admin\/([^'\"]+)\.js", r"from './admin/\1.vue'", script)
    
    script = script.strip()
    
    # Clean up empty lines
    while '\n\n\n' in script:
        script = script.replace('\n\n\n', '\n\n')
    
    vue_content = f"<template>\n{template}\n</template>\n\n<script>\n{script}\n</script>\n"
    
    vue_path.parent.mkdir(parents=True, exist_ok=True)
    vue_path.write_text(vue_content, encoding='utf-8')
    return True

def main():
    files = sorted(SRC.glob("*.js"))
    done = 0
    for f in files:
        vue_path = DST / (f.stem + ".vue")
        if convert_file(f, vue_path):
            print(f"  {f.name} → {vue_path.name}")
            done += 1
    print(f"\nDone: {done}/{len(files)}")

if __name__ == "__main__":
    main()
