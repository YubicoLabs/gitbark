from wrappers.git_wrapper import GitWrapper

class ReferenceUpdate:
    def __init__(self, params) -> None:
        self.git = GitWrapper()
        old_ref, new_ref, ref_name = self.get_ref_update_params(params)
        self.old_ref = old_ref
        self.new_ref = new_ref
        self.ref_name = ref_name

    def get_ref_update_params(self, params):
        old_ref = None
        new_ref = None
        ref_name = None
        if params:
            old_ref, new_ref, ref_name = params.split()
        return old_ref, new_ref, ref_name

    def reset_update(self):
        self.git.update_ref(self.ref_name, self.old_ref, self.new_ref)

