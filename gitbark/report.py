from .git.reference_update import ReferenceUpdate

class BranchReport:

    def __init__(self, branch) -> None:
        self.branch = branch
        self.branch_rule_violations = []
        self.commit_rule_violations = []
        self.ref_update = None
    
    def add_branch_rule_violation(self, violation) -> None:
        self.branch_rule_violations.append(violation)
    
    def add_commit_rule_violation(self, violation) -> None:
        self.commit_rule_violations.append(violation)
    
    def add_reference_reset(self, ref_update:ReferenceUpdate) -> None:
        self.ref_update = ref_update

    def print_reference_reset(self):
        if self.ref_update and self.ref_update.exit_status:
            print(f"\nRejected incoming change due to rule violations.")

    def print_commit_rule_violations(self) -> None:
        for violation in self.commit_rule_violations:
            print("  -",  violation)
    
    def print_branch_rule_violations(self) -> None:
        for violation in self.branch_rule_violations:
            print("  -", violation)

class Report:

    def __init__(self) -> None:
        self.output = {}

    def print_report(self) -> None:
        if self.output:
            for branch in self.output.keys():
                branch_report = self.__get_branch(branch)
                print()
                if branch_report.ref_update:
                    if branch_report.ref_update.is_on_local_branch():
                        if branch_report.ref_update.from_remote():
                            print(f"Error: Incoming change on {branch} with commit ID {branch_report.ref_update.new_ref} violates the following rules: ")
                        else:
                            print(f"Warning: Incoming change on {branch} with commit ID {branch_report.ref_update.new_ref} violates the following rules: ")
                else:
                    print(f"Warning: {branch} is invalid. The following rules are violated: ")

                branch_report.print_branch_rule_violations()
                branch_report.print_commit_rule_violations()
                branch_report.print_reference_reset()
                print()
        else:
            print("Repository is in a valid state")

    def __add_branch(self, branch) -> None:
        if not branch in self.output:
            self.output[branch] = BranchReport(branch)
    
    def __get_branch(self, branch) -> BranchReport:
        return self.output[branch]

    def add_branch_rule_violations(self, branch, violations) -> None:
        if not branch in self.output:
            self.__add_branch(branch)
        branch_report = self.__get_branch(branch)
        for violation in violations:
            branch_report.add_branch_rule_violation(violation)
    
    def add_commit_rule_violations(self, branch, violations):
        if not branch in self.output:
            self.__add_branch(branch)
        branch_report = self.__get_branch(branch)
        for violation in violations:
            branch_report.add_commit_rule_violation(violation)

    def add_branch_reference_reset(self, branch, ref_update:ReferenceUpdate):
        if not branch in self.output:
            self.__add_branch(branch)
        
        branch_report = self.__get_branch(branch)
        branch_report.add_reference_reset(ref_update)

    
    


    

        
        

    

    
