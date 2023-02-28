class Report:

    # 
    # {
    #   branches: {
    #      main: {
    #        title: 
    #      }
    #   } 
    #  
    # }
    def __init__(self) -> None:
        self.output = {}

    def add(self, branch):
        if not "branches" in self.output:
            self.output["branches"] = {}

        if not branch in self.output["branches"]:
            self.output["branches"][branch] = {}
        
        
        

    

    
