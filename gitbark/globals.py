from .wd import WorkingDirectory

def init():
    """
    Initialize global working directory
    """
    global working_directory 
    working_directory = WorkingDirectory()