
import importlib
from gitbark.git.commit import Commit
from .rule import Rule, CompositeRule

# This is temporary. Eventually, entrypoints will be loaded and saved when 
# installing the system. 
rule_to_entrypoint = {
    "require_signature": "gitbark.bark_core.signatures.require_signature",
    "file_not_modified": "gitbark.bark_core.files.file_not_modified",
    "disallow_invalid_parents": "gitbark.bark_core.parents.disallow_invalid_parents"
}


def get_rules(commit: Commit) -> list[Rule]:
    rules_yaml = commit.get_rules()
    rules = []

    for rule in rules_yaml["rules"]:
        # If sub-rule 
        if "any" in rule:
            any_rules_yaml = rule["any"]
            any_rule_name = ""
            if "name" in any_rules_yaml:
                any_rule_name = any_rules_yaml["name"]
            else:
                any_rule_name = "ANY"
            composite_rule = CompositeRule(any_rule_name)
            for sub_rule in any_rules_yaml:
                new_sub_rule = create_rule(sub_rule)
                composite_rule.add_sub_rule(new_sub_rule)
            rules.append(composite_rule)
        else:
            new_rule = create_rule(rule)
            rules.append(new_rule)
    
    return rules

def load_rule_module(rule_name):
    module_name = rule_to_entrypoint[rule_name]
    module = importlib.import_module(module_name)
    return getattr(module, 'Rule')

def create_rule(rule):
    rule_name = rule["rule"]    
    rule_args = {k: v for k, v in rule.items() if not k == "rule"}

    rule_module = load_rule_module(rule_name)
    return rule_module(rule_name, rule_args)

