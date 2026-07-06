#!/usr/bin/env python3
"""
build_module.py

Script to bundle all files in the microspade/ directory into a single
microspade.py file for easy deployment on the micro:bit, or build them
separately as flat modules.
"""

import os
import re
import ast
import sys
import shutil

FILES_ORDER = [
    "ms_mailbox.py",
    "ms_message.py",
    "ms_transport.py",
    "ms_container.py",
    "ms_agent.py",
    "ms_artifact.py",
    "ms_behaviour.py",
    "ms_cyclic.py",
    "ms_oneshot.py",
    "ms_periodic.py",
    "ms_timeout.py",
    "ms_fsm.py",
    "ms_log.py",
]

class ImportTransformer(ast.NodeTransformer):
    IMPORT_MAPPING = {
        "Agent": "ms_agent",
        "Artifact": "ms_artifact",
        "RemoteArtifactProxy": "ms_artifact",
        "Behaviour": "ms_behaviour",
        "CyclicBehaviour": "ms_cyclic",
        "OneShotBehaviour": "ms_oneshot",
        "PeriodicBehaviour": "ms_periodic",
        "TimeoutBehaviour": "ms_timeout",
        "FSMBehaviour": "ms_fsm",
        "State": "ms_fsm",
        "Message": "ms_message",
        "MessageTemplate": "ms_message",
        "Mailbox": "ms_mailbox",
        "RadioTransport": "ms_transport",
        "container": "ms_container",
        "log_kb": "ms_log",
    }


    MODULE_MAPPING = {
        "agent": "ms_agent",
        "artifact": "ms_artifact",
        "behaviour": "ms_behaviour",
        "cyclic_behaviour": "ms_cyclic",
        "oneshot_behaviour": "ms_oneshot",
        "periodic_behaviour": "ms_periodic",
        "timeout_behaviour": "ms_timeout",
        "fsm_behaviour": "ms_fsm",
        "message": "ms_message",
        "mailbox": "ms_mailbox",
        "transport": "ms_transport",
        "container": "ms_container",
        "log": "ms_log",
    }

    def visit_ImportFrom(self, node):
        if node.module == "microspade":
            # Group imported names by their target modules (flat modules)
            modules_to_names = {}
            for alias in node.names:
                name = alias.name
                target_module = self.IMPORT_MAPPING.get(name)
                if target_module:
                    if target_module not in modules_to_names:
                        modules_to_names[target_module] = []
                    modules_to_names[target_module].append(alias)
                else:
                    if "microspade" not in modules_to_names:
                        modules_to_names["microspade"] = []
                    modules_to_names["microspade"].append(alias)
            
            # Generate new ImportFrom nodes
            new_nodes = []
            for target_module, aliases in modules_to_names.items():
                new_nodes.append(
                    ast.ImportFrom(
                        module=target_module,
                        names=aliases,
                        level=0
                    )
                )
            return new_nodes

        elif node.module and node.module.startswith("microspade."):
            # Change from microspade.xyz to flat module name
            submodule = node.module[len("microspade."):]
            node.module = self.MODULE_MAPPING.get(submodule, submodule)
            return node

        return node

def minify_and_transform(content, debug_mode=False):
    """Remove comments/docstrings and transform imports from microspade to flat submodules."""
    tree = ast.parse(content)
    
    # Remove docstrings
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
                if not node.body and isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    node.body.append(ast.Pass())
                    
    # Remove debug functions (like __repr__) if not in debug mode
    if not debug_mode:
        class DebugStripper(ast.NodeTransformer):
            def visit_FunctionDef(self, node):
                if node.name == "__repr__":
                    return None
                return self.generic_visit(node)
        tree = DebugStripper().visit(tree)
        ast.fix_missing_locations(tree)

    # Transform imports
    transformer = ImportTransformer()
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)
    
    return ast.unparse(tree)

def resolve_dependencies(dest_main_path, modular_dist_dir):
    """
    Recursively find all modular dependencies of the main script by parsing AST.
    Returns a set of filenames (e.g., {'agent.py', 'behaviour.py'}).
    """
    valid_modules = {filename[:-3]: filename for filename in FILES_ORDER}
    dependencies = set()
    queue = []
    
    # Start with main.py if it exists
    if os.path.exists(dest_main_path):
        queue.append(('main', dest_main_path))
        
    while queue:
        mod_name, filepath = queue.pop(0)
        
        if not os.path.exists(filepath):
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
        except Exception as e:
            print(f"Warning: Could not parse {filepath} to resolve dependencies: {e}")
            continue
            
        for node in ast.walk(tree):
            dep_name = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_name = alias.name.split('.')[0]
                    if base_name in valid_modules:
                        dep_name = base_name
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_name = node.module.split('.')[0]
                    if base_name in valid_modules:
                        dep_name = base_name
                        
            if dep_name:
                filename = valid_modules[dep_name]
                if filename not in dependencies:
                    dependencies.add(filename)
                    dep_path = os.path.join(modular_dist_dir, filename)
                    queue.append((dep_name, dep_path))
                    
    return dependencies

def main():
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(tools_dir)
    src_dir = os.path.join(root_dir, "microspade")
    output_dir = os.path.join(root_dir, "dist")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse optional debug mode
    debug_mode = False
    if "--debug" in sys.argv:
        debug_mode = True
        sys.argv.remove("--debug")
    elif "-debug" in sys.argv:
        debug_mode = True
        sys.argv.remove("-debug")

    # Parse optional user script/project path
    user_script_path = None
    if len(sys.argv) > 1:
        arg_path = sys.argv[1]
        if not os.path.isabs(arg_path):
            arg_path = os.path.abspath(os.path.join(os.getcwd(), arg_path))
            
        if os.path.isdir(arg_path):
            main_py = os.path.join(arg_path, "main.py")
            if os.path.exists(main_py):
                user_script_path = main_py
            else:
                print(f"Error: main.py not found in {arg_path}")
                sys.exit(1)
        elif os.path.isfile(arg_path):
            user_script_path = arg_path
        else:
            print(f"Error: path not found {arg_path}")
            sys.exit(1)

    # 1. Output the single-file bundled module (fallback/legacy)
    output_path = os.path.join(output_dir, "microspade.py")
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
            
        print(f"Processing and minifying for bundle: {filename}...")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            content = minify_and_transform(content, debug_mode)
        except Exception as e:
            print(f"Warning: could not minify {filename} due to {e}")
            
        # Remove internal imports (for the single bundle)
        lines = content.splitlines()
        filtered_lines = []
        for line in lines:
            if re.match(r'^\s*from\s+(microspade|ms_[a-zA-Z0-9_]+)\b', line):
                continue
            if re.match(r'^\s*import\s+(microspade|ms_[a-zA-Z0-9_]+)\b', line):
                continue
            filtered_lines.append(line)
            
        bundled_content.append(f"# --- Section: {filename} ---")
        bundled_content.extend(filtered_lines)
        bundled_content.append("")
        
    bundled_content.append("# --- Exports ---")
    bundled_content.append('__version__ = "0.1.0"')
    bundled_content.append("")
    bundled_content.append("__all__ = [")
    for item in [
        "Agent", "CyclicBehaviour", "OneShotBehaviour", "PeriodicBehaviour",
        "TimeoutBehaviour", "FSMBehaviour", "State", "Message", "MessageTemplate",
        "RadioTransport", "container"
    ]:
        bundled_content.append(f'    "{item}",')
    bundled_content.append("]")
    bundled_content.append("")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(bundled_content))
    print(f"Successfully generated single-file module: {output_path}")

    # 2. Output the modular package in dist/microspade/
    modular_dist_dir = os.path.join(output_dir, "microspade")
    os.makedirs(modular_dist_dir, exist_ok=True)

    init_path = os.path.join(modular_dist_dir, "__init__.py")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write("# microbit-module: microspade@0.1.0\n")

    for filename in FILES_ORDER:
        filepath = os.path.join(src_dir, filename)
        dest_path = os.path.join(modular_dist_dir, filename)
        module_name = filename[:-3]
        
        print(f"Generating modular module: {filename}...")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            content = minify_and_transform(content, debug_mode)
        except Exception as e:
            print(f"Warning: could not minify {filename} due to {e}")

        # Prepend the micro:bit module header comment (flat module name)
        header = f"# microbit-module: {module_name}@0.1.0\n"
        content = header + content
                
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    print(f"Successfully generated modular package in: {modular_dist_dir}")

    # 3. Process the user script if provided
    if user_script_path:
        dest_main_path = os.path.join(output_dir, "main.py")
        print(f"Processing user script: {user_script_path}...")
        with open(user_script_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            content = minify_and_transform(content, debug_mode)
        except Exception as e:
            print(f"Warning: could not process user script due to {e}")
            
        with open(dest_main_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully built user script to: {dest_main_path}")

    # 4. Resolve dependencies if main.py was processed
    dependencies_path = os.path.join(output_dir, "dependencies.txt")
    if user_script_path:
        dest_main_path = os.path.join(output_dir, "main.py")
        print("Resolving required dependencies...")
        deps = resolve_dependencies(dest_main_path, modular_dist_dir)
        with open(dependencies_path, "w", encoding="utf-8") as f:
            for dep in sorted(deps):
                f.write(f"{dep}\n")
        print(f"Generated dependency list ({len(deps)} modules): {dependencies_path}")
        print("Required modules:", sorted(deps))
    else:
        # If no user script was built, remove old dependencies.txt if it exists
        if os.path.exists(dependencies_path):
            try:
                os.remove(dependencies_path)
            except:
                pass

if __name__ == "__main__":
    main()
