#!/usr/bin/env python3
"""
This is a hack (or seems like one) to allow models to be defined in different
Python modules - import Base from this and use that as the subclass for your
models.

https://stackoverflow.com/questions/51106264/how-do-i-split-an-sqlalchemy-declarative-model-into-modules
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
