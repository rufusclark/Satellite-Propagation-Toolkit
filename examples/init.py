"""append project root path to PYTHONPATH

this allows scripts located in child directories to be called from the root directory

this script has side-effects"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
