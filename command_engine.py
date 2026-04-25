class CommandEngine:
    def __init__(self, prefix):
        self.prefix = prefix
        self.commands = {}
    
    def register(self, name):
        def decorator(func):
            self.commands[name] = func
            return func
        return decorator
    
    def execute(self, cmd_name, args_text=""):
        func = self.commands.get(cmd_name)
        if not func:
            return f"Неизвестная команда: {self.prefix}{cmd_name}"
        if args_text:
            return func(args_text)
        return func()