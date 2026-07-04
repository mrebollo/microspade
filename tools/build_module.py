#!/usr/bin/env python3
"""
build_module.py

Script to bundle all files in the microspade/ directory into a single
microspade.py file for easy deployment on the micro:bit.
"""

import os
import re
import ast

FILES_ORDER = [
    "_compat.py",
    "mailbox.py",
    "message.py",
    "transport.py",
    "container.py",
    "artifact.py",
    "behaviour.py",
    "agent.py",
]

def minify(content):
    """Remove comments and docstrings from Python source code using AST."""
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
                if not node.body and isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    node.body.append(ast.Pass())
    return ast.unparse(tree)

def main():
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(tools_dir)
    src_dir = os.path.join(root_dir, "microspade")
    output_dir = os.path.join(root_dir, "dist")
    output_path = os.path.join(output_dir, "microspade.py")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    bundled_content = [
        '# microbit-module: microspade@0.1.0',
        '"""',
        'microspade — SPADE-like agents for micro:bit.',
        'Bundled single-file module.',
        '"""',
        "",
    ]
    
    for filename in FILES_ORDER:
        filepath = os.path.join(src_dir, filename)
        if not os.path.exists(filepath):
            print(f"Error: {filepath} not found.")
            return
            
        print(f"Processing and minifying {filename}...")
        if filename == "_compat.py":
            content = "from utime import ticks_ms, ticks_diff, sleep_ms"
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                content = minify(content)
            except Exception as e:
                print(f"Warning: could not minify {filename} due to {e}")
            
        # Remove internal imports
        lines = content.splitlines()
        filtered_lines = []
        for line in lines:
            # Match imports like: from microspade.xxx import yyy
            if re.match(r'^\s*from\s+microspade\b', line):
                continue
            if re.match(r'^\s*import\s+microspade\b', line):
                continue
            filtered_lines.append(line)
            
        bundled_content.append(f"# --- Section: {filename} ---")
        bundled_content.extend(filtered_lines)
        bundled_content.append("")
        
    # Append __all__ and version
    bundled_content.append("# --- Exports ---")
    bundled_content.append('__version__ = "0.1.0"')
    bundled_content.append("")
    bundled_content.append("__all__ = [")
    bundled_content.append('    "Agent",')
    bundled_content.append('    "CyclicBehaviour",')
    bundled_content.append('    "OneShotBehaviour",')
    bundled_content.append('    "PeriodicBehaviour",')
    bundled_content.append('    "TimeoutBehaviour",')
    bundled_content.append('    "FSMBehaviour",')
    bundled_content.append('    "State",')
    bundled_content.append('    "Message",')
    bundled_content.append('    "MessageTemplate",')
    bundled_content.append('    "RadioTransport",')
    bundled_content.append('    "container",')
    bundled_content.append("]")
    bundled_content.append("")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(bundled_content))
        
    print(f"Successfully generated single-file module: {output_path}")

if __name__ == "__main__":
    main()
