import subprocess
import functools
import asyncio
from .converters import executor

class UpdatedPackage:
    def __init__(self, name, old, new):
        self.name = name
        self.old_version = old
        self.new_version = new

    @property
    def updated(self):
        return self.old_version != self.new_version

    def __repr__(self):
        if not self.updated:
            return f"<Package name={self.name}, updated={self.updated}>"
        else:
            return f"<Package name={self.name}, before={self.old_version}, after={self.new_version}, updated={self.updated}>"

@executor
def update(package):
    p = subprocess.Popen(['pip', 'install', '-U', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    old_version = None
    new_version = None
    if package.startswith("git+"):
        package = package.split('/')[-1].removesuffix('.git')
    out = out.decode('utf-8').strip()
    lines = out.splitlines()
    for line in lines:
        if line.strip().lower().startswith(f"found existing installation: {package}".lower()):
            old_version = line.split(' ')[-1]
        if line.strip().startswith(f"Successfully installed {package}"):
            new_version = line.strip().removeprefix(f"Successfully installed {package}-")
    return UpdatedPackage(package, old_version, new_version)

@executor
def run(line):
    p = subprocess.Popen(line.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    out = out.decode('utf-8').strip()
    return out
