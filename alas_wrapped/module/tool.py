class Tool:
    def __init__(self, name: str, description: str, execute: callable, parameters: list = None):
        """
        Initializes a Tool.

        Args:
            name (str): The name of the tool.
            description (str): A description of what the tool does.
            execute (callable): The function to execute when the tool is called.
            parameters (list, optional): A list of parameters the tool accepts. Defaults to None.
        """
        self.name = name
        self.description = description
        self.execute = execute
        self.parameters = parameters if parameters is not None else []

    def __call__(self, *args, **kwargs):
        """
        Executes the tool's function.
        """
        return self.execute(*args, **kwargs)

    def __str__(self):
        return f"Tool(name={self.name})"
