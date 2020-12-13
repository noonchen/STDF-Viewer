#
# PySTDF - The Pythonic STDF Parser
# Copyright (C) 2006 Casey Marshall
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import sys

from deps.pystdf import TableTemplate

import pdb

logicalTypeMap = {
  "C1": "Char",
  "B1": "UInt8",
  "U1": "UInt8",
  "U2": "UInt16",
  "U4": "UInt32",
  "U8": "UInt64",
  "I1": "Int8",
  "I2": "Int16",
  "I4": "Int32",
  "I8": "Int64",
  "R4": "Float32",
  "R8": "Float64",
  "Cn": "String",
  "Bn": "List",
  "Dn": "List",
  "Vn": "List"
}

# convert stdf data types to struct(module) formats
packFormatMap = {
  "C1": "c",
  "B1": "B",
  "U1": "B",
  "U2": "H",
  "U4": "I",
  "U8": "Q",
  "I1": "b",
  "I2": "h",
  "I4": "i",
  "I8": "q",
  "R4": "f",
  "R8": "d"
}

def stdfToLogicalType(fmt):
  if fmt.startswith('k'):
    return 'List'
  else:
    return logicalTypeMap[fmt]

class RecordHeader:
  def __init__(self):
    self.len=0
    self.typ=0
    self.sub=0
  
  def __repr__(self):
    return "<STDF Header, REC_TYP=%d REC_SUB=%d REC_LEN=%d>" % (self.typ, self.sub, self.len) 

class RecordType(TableTemplate):
  def __init__(self):
    # columnNames: the list of data names in a record, e.g.: [CPU_TYP, ...]
    # columntypes: the list of data types in a record, e.g.: [U1, ...]
    TableTemplate.__init__(self, 
      [name for name, stdfType in self.fieldMap], 
      [stdfToLogicalType(stdfTyp) for name, stdfTyp in self.fieldMap])
  
class UnknownRecord(TableTemplate):
  def __init__(self, rec_typ, rec_sub):
    TableTemplate.__init__(self, [], [], 'UnknownRecord')
    self.rec_typ = rec_typ
    self.rec_sub = rec_sub

class EofException(Exception): pass

class EndOfRecordException(Exception): pass

class InitialSequenceException(Exception): pass

class StdfRecordMeta(type):
  """Generate the necessary plumbing for STDF record classes 
  based on simple, static field defintions.
  This enables a simple, mini-DSL (domain-specific language)
  approach to defining STDF records.
  I did this partly to learn what metaclasses are good for,
  partly for fun, and partly because I wanted end users to be
  able to easily define their own custom STDF record types.
  """
  def __init__(cls, name, bases, dct):
    # <name> specifies the class name. This becomes the __name__ attribute of the class.
    # <bases> specifies a tuple of the base classes from which the class inherits. This becomes the __bases__ attribute of the class.
    # <dct> specifies a namespace dictionary containing definitions for the class body. This becomes the __dict__ attribute of the class.
    # Map out field definitions
    fieldMap = dct.get('fieldMap', [])
    for i, fieldDef in enumerate(fieldMap):
      setattr(cls, fieldDef[0], i)
    setattr(cls, 'fieldFormats', dict(fieldMap))
    setattr(cls, 'fieldNames', [field_name for field_name, field_type in fieldMap])
    setattr(cls, 'fieldStdfTypes', [field_type for field_name, field_type in fieldMap])
    
    # Add initializer for the generated class
    setattr(cls, '__init__', lambda _self: RecordType.__init__(_self))
    
    # Proceed with class generation
    return super(StdfRecordMeta, cls).__init__(name, bases, dct)
    
