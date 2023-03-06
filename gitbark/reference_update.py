from .git_api import GitApi
from .commit import Commit

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
        # TODO: Add som error validation
        self.git = GitApi()
        old_ref, new_ref, ref_name = self.get_ref_update_params(params)
        self.old_ref = old_ref
        self.new_ref = new_ref
        self.ref_name:str = ref_name
        self.exit_status = 0

    def __str__(self) -> str:
        res = f"Reference update on {self.ref_name}: {self.old_ref} -> {self.new_ref}"
        return res
    
    
    def from_remote(self):
        """Returns true if local branch is updated with changes from remote
        
        Fast-forward: local head is updated to head of remote
        Three-way-merge: parents of local head point to previous local head and head of remote
        """

        if not self.is_on_local_branch():
            return False

        # Fast-foward
        remote_refs = self.git.get_remote_refs().split()
        if self.new_ref in remote_refs:
            return True
        
        # Three-way-merge
        local_head = Commit(self.new_ref)
        # prev_head = self.old_ref
        parents = local_head.get_parents()
        if len(parents) > 1:
            parent_hashes = [parent.hash for parent in parents]
            for hash in parent_hashes:
                if hash in remote_refs:
                    return True


        return False

    def get_ref_update_params(self, params):
        """Returns the reference update parameters"""
        old_ref = None
        new_ref = None
        ref_name = None
        if params:
            old_ref=params[0]
            new_ref=params[1]
            ref_name=params[2]
            #old_ref, new_ref, ref_name = params.split()
        return old_ref, new_ref, ref_name

    def is_on_local_branch(self):
        return self.ref_name.startswith('refs/heads')

    def reset_update(self):
        """Resets the reference update"""
        if self.from_remote():
            self.exit_status = 1
        else:
            self.exit_status = 2
