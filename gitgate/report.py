from .reference_update import ReferenceUpdate

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
        if self.ref_update:
            print(f"{self.ref_update} was rejected")

    def print_commit_rule_violations(self) -> None:
        if len(self.commit_rule_violations) > 0:
            print("Commit rule violations:")
        for violation in self.commit_rule_violations:
            print(violation)
    
    def print_branch_rule_violations(self) -> None:
        if len(self.branch_rule_violations) > 0:
            print("Branch rule violations:")
        for violation in self.branch_rule_violations:
            print(violation)

class Report:

    def __init__(self) -> None:
        self.output = {}

    def print_report(self) -> None:
        if self.output:
            for branch in self.output.keys():
                print(f"Warning: {branch} is invalid")
                branch_report = self.__get_branch(branch)
                branch_report.print_branch_rule_violations()
                branch_report.print_commit_rule_violations()
                branch_report.print_reference_reset()
                print()
        else:
            print("Incoming change is valid")



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
    
    


    

        
        

    

    
