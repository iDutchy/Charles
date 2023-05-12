class ModAction:
    def __init__(self, *args, **kwargs):
        self.target = kwargs.get('target')
        self.targets = kwargs.get('targets')
        self.mod = kwargs.get("mod")
        self.reason = kwargs.get('reason')
        self.guild = kwargs.get("guild")
        self.failed = kwargs.get("failed")