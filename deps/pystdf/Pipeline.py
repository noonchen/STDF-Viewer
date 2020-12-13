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

def appendPrefixAction(fn, ds, action):
  """Create a function that injects a call to 'action' prior to given function 'fn'"""
  def new_fn(*args):
    action(ds, *args)
    fn(*args)
  return new_fn

def appendSuffixAction(fn, sink, action):
  """Create a function that injects a call to 'action' following given function 'fn'"""
  def new_fn(*args):
    fn(*args)
    action(sink, *args)
  return new_fn

class EventSource:
  """EventSource
  A generic base class for something that originates events (a source)
  and broadcasts them to receivers (the sinks).  Events are propagated
  as method calls.  Event sinks can receieve notification before or
  after the event occurs.
  
  Registration is achieved by a contract of method name convention.
  The sink defines methods based on the event name in order to receive it.
  Event method names in the sink with a 'before_' prefix will be invoked
  prior to the event occuring, similarly, a method with the 'after_' suffix
  will be invoked after the event occurs."""
  
  def __init__(self, eventNames):
    self.eventNames = eventNames
  
  def addSink(self, sink):
    # sink: a class
    # This method is for add prefix and suffix method 
    # for all events methods if there are any.
    "Register a DataSink to receive the events it has defined"
    for eventName in self.eventNames:
      preEventName = 'before_' + eventName
      postEventName = 'after_' + eventName
      if hasattr(sink, preEventName):
        # self.eventName() = preEventName(self, *args); eventName(*args)
        setattr(self, eventName, 
          appendPrefixAction(
              getattr(self, eventName),
              self, getattr(sink, preEventName)))
      if hasattr(sink, postEventName):
        setattr(self, eventName, 
          appendSuffixAction(
              getattr(self, eventName),
              self, getattr(sink, postEventName)))

class DataSource(EventSource):
  
  def __init__(self, add_events=[]):
    EventSource.__init__(self, ['begin', 'send', 'complete', 'cancel'] + add_events)
  
  def begin(self, data): pass
  
  def send(self, data): pass
  
  def complete(self): pass
  
  def cancel(self, exception): pass
  
