#! /usr/bin/env python

"""Build a debootstrap script from a list of base packages and a control
file listing per-architecture overrides."""

import sys
import os
import string
import re

class RequiredPackageNotInBase(Exception): pass

class Base:
    def __init__(self):
        self.base = {}

    def read(self, f):
        """Read a file describing the base system on each architecture."""
        for line in f:
            line = line.rstrip()
            if line.startswith('#') or len(line) == 0:
                continue

            fields = line.split(':')
            if len(fields) != 2:
                continue

            name = fields[0]
            value = fields[1].strip()
            packages = value.split()

            if name.startswith('base-'):
                arch = name[5:]
                if arch not in self.base:
                    self.base[arch] = []
                self.base[arch].extend(packages)

        f.close()

class Overrides:
    def __init__(self):
        self.exclude = []
        self.required = []

        self.arch_exclude = {}
        self.arch_required = {}

    def read(self, f):
        """Read an overrides file."""
        for line in f:
            line = line.rstrip()
            if line.startswith('#') or len(line) == 0:
                continue

            fields = line.split(':')
            if len(fields) != 2:
                continue

            name = fields[0]
            value = fields[1].strip()
            packages = value.split()

            if name == 'exclude':
                # Exclude from all architectures (regular expressions)
                for expr in packages:
                    self.exclude.append(re.compile(expr))
            elif name.startswith('exclude-'):
                # Exclude from one architecture (regular expressions)
                arch = name[8:]
                if arch not in self.arch_exclude:
                    self.arch_exclude[arch] = []
                for expr in packages:
                    self.arch_exclude[arch].append(re.compile(expr))
            elif name == 'required':
                # Required in first stage on all architectures
                self.required.extend(packages)
            elif name.startswith('required-'):
                # Required in first stage on one architecture
                arch = name[9:]
                if arch not in self.arch_required:
                    self.arch_required[arch] = []
                self.arch_required[arch].extend(packages)
            elif name.startswith('base-'):
                # In base system (second stage) on one architecture
                arch = name[5:]
                if arch not in self.arch_base:
                    self.arch_base[arch] = []
                self.arch_base[arch].extend(packages)

        f.close()

def main():
    for dist in sys.argv[1:]:
        template_name = "%s.template" % dist
        base_name = "%s.base" % dist
        overrides_name = "%s.overrides" % dist

        # Read base system
        base = Base()
        if os.path.exists(base_name):
            base.read(open(base_name, 'r'))

        # Read overrides
        overrides = Overrides()
        if os.path.exists(overrides_name):
            overrides.read(open(overrides_name, 'r'))

        base_arch_indep = []
        base_arch_dep = {}
        required_arch_indep = []
        required_arch_dep = {}

        for arch in base.base:
            base_arch_dep[arch] = []
            required_arch_dep[arch] = []

        # Process excludes first.
        for arch in base.base:
            excludes = list(overrides.exclude)
            if arch in overrides.arch_exclude:
                excludes.extend(overrides.arch_exclude[arch])
            new_base = []
            for package in base.base[arch]:
                for exclude in excludes:
                    if exclude.match(package):
                        break
                else:
                    new_base.append(package)
            base.base[arch] = new_base

        # Sketch out the whole base system.
        base_full = []
        for arch in base.base:
            for package in base.base[arch]:
                if package not in base_full:
                    base_full.append(package)

        # Which packages are in the base system on only some architectures?
        for package in base_full:
            for arch in base.base:
                if package not in base.base[arch]:
                    break
            else:
                base_arch_indep.append(package)

        # By set subtraction, get the architecture-dependent list for each
        # architecture.
        for arch in base.base:
            for package in base.base[arch]:
                if package not in base_arch_indep:
                    base_arch_dep[arch].append(package)

        # Move architecture-independent requires. If they actually aren't
        # available on all architectures, make them architecture-dependent
        # requires instead.
        for package in overrides.required:
            if package in base_arch_indep:
                base_arch_indep.remove(package)
                required_arch_indep.append(package)
            else:
                for arch in base_arch_dep:
                    if package in base_arch_dep[arch]:
                        base_arch_dep[arch].remove(package)
                        required_arch_dep[arch].append(package)
                # TODO: would like to raise an exception if it wasn't in
                # base_arch_dep at all

        # Move architecture-dependent requires.
        for arch in overrides.arch_required:
            for package in overrides.arch_required[arch]:
                if package in base_arch_indep:
                    # Required on one architecture; base elsewhere.
                    base_arch_indep.remove(package)
                    for otherarch in base_arch_dep:
                        if arch != otherarch:
                            base_arch_dep[otherarch].append(package)
                    required_arch_dep[arch].append(package)
                else:
                    # Required on one architecture; may or may not be base
                    # elsewhere, but we don't need to care.
                    if package in base_arch_dep[arch]:
                        base_arch_dep[arch].remove(package)
                        required_arch_dep[arch].append(package)
                    else:
                        raise RequiredPackageNotInBase, package

        # Make substitutions in the template
        template_handle = open(template_name, 'r')
        template = template_handle.read()
        template_handle.close()

        updist = dist.upper()
        template = template.replace("@%s_REQUIRED@" % updist, string.join(required_arch_indep))
        template = template.replace("@%s_BASE@" % updist, string.join(base_arch_indep))
        for arch in required_arch_dep:
            template = template.replace("@%s_REQUIRED_%s@" % (updist, arch.upper()), string.join(required_arch_dep[arch]))
        for arch in base_arch_dep:
            template = template.replace("@%s_BASE_%s@" % (updist, arch.upper()), string.join(base_arch_dep[arch]))

        output_handle = open(dist, 'w')
        output_handle.write(template)
        output_handle.close()

if __name__ == "__main__":
    main()
