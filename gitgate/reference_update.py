from .git_api import GitApi

class ReferenceUpdate:
    """Git reference update class
    
    This class serves as a wrapper for a Git reference-update 
    """
    def __init__(self, params) -> None:
        """Init ReferenceUpdate with Git reference-update object
        
        Attributes
        ----------
        old_ref: str
            the value of the old reference pointer
        new_ref: str
            the value of the new reference pointer
        ref_name: str
            the name of the ref that is to be updated
        """
        self.git = GitApi()
        old_ref, new_ref, ref_name = self.get_ref_update_params(params)
        self.old_ref = old_ref
        self.new_ref = new_ref
        self.ref_name:str = ref_name

    def __str__(self) -> str:
        res = f"Reference update on {self.ref_name}: {self.old_ref} -> {self.new_ref}"
        return res

    def get_ref_update_params(self, params):
        """Returns the reference update parameters"""
        old_ref = None
        new_ref = None
        ref_name = None
        if params:
            old_ref, new_ref, ref_name = params.split()
        return old_ref, new_ref, ref_name

    def is_on_local_branch(self):
        return self.ref_name.startswith('refs/heads')

    def reset_update(self):
        """Resets the reference update"""
        self.git.update_ref(self.ref_name, self.old_ref)

