"""clawparity: the shared differential-comparison library.

A family supplies a specification (JSON) and test cases (Python). This library
runs each case twice from identical memory: once through the native module and
once through the original instructions under emulation, and requires the same
ordered outside calls, the same memory and the same return value.
"""

# The public build-input API adds opt-in sharing around the unchanged owned-input
# implementation, so existing admissions keep their original build semantics.
from . import shared_build_inputs as build_inputs
