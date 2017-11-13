# MIT License
#
# Copyright (c) 2017 Matthias Rost, Alexander Elvers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__author__ = "Matthias Rost, Alexander Elvers (mrost / aelvers <AT> inet.tu-berlin.de)"

import inspect
import types
import copy
import collections

def checkPercentage(value, noneAllowed=True):
    if noneAllowed and value is None:
        return
    if not isinstance(value, float):
        raise Exception("Bad Type")
    if value < 0.0 or value > 1.0:
        raise Exception("Bad Type")

def checkPosFloat(value, noneAllowed=True):
    if noneAllowed and value is None:
        return
    if not isinstance(value, (int,float)):
        raise Exception("Bad Type" + str(value))
    if value < 0.0:
        raise Exception("Bad Type")

def checkPosInt(value, noneAllowed=True):
    if noneAllowed and value is None:
        return
    if not isinstance(value, int):
        raise Exception("Bad Type")
    if value < 0:
        raise Exception("Bad Type")

def checkIntWithRange(value, min, max, noneAllowed=True):
    if noneAllowed and value is None:
        return
    if not isinstance(value, int):
        raise Exception("Bad Type")
    if value < min:
        raise Exception("Bad Type")
    if value > max:
        raise Exception("Bad Type")

def checkBool(value, noneAllowed=True):
    if noneAllowed and value is None:
        return
    if not isinstance(value, bool):
        raise Exception("Bad Type")



def prettyPrint(obj, indentOffset=0, indentStep=2):

    string, objects = _prettyPrint(obj, indentOffset=indentOffset, indentStep=indentStep, knownObjects=set())
    print(string)
    return string


def _prettyPrint(obj, indentOffset=0, indentStep=2, knownObjects=set()):

    string=""

    header = " " * indentOffset
    headerBelow = " " * (indentOffset + indentStep)


    objectsThatNeedToBeDescribed = []
    string += "\n" + header + obj.__module__ + "." + obj.__class__.__name__ + " @ " + hex(id(obj)) + "\n"
    for attr in sorted(obj.__dict__):
        position = 0
        value = getattr(obj, attr)

        if hasattr(value, "__class__") and hasattr(value, "__module__"):
            if ("algorithms" in value.__module__ or "datamodel" in value.__module__ or "input" in value.__module__ or
                 "util" in value.__module__ ):
                if value not in knownObjects:
                    objectsThatNeedToBeDescribed.append(value)
                    position = 1
                else:
                    position = -1

        if position == -1:
            string += headerBelow + "{0}: {1} [see above]".format(attr, value)
        elif position == 0:
                string += headerBelow + "{0}: {1} ".format(attr, value)
        elif position == 1:
            string += headerBelow + "{0}: {1} [see below]".format(attr, value)
        else:
            raise Exception("Unknown position!")



        if isinstance(value, collections.Iterable) and not isinstance(value, str):
            #print headerBelow + " .. items:"
            count = False
            for subValue in value:
                newValue = subValue
                if isinstance(value, dict):
                    newValue = value[subValue]
                if hasattr(newValue, "__class__") and hasattr(newValue, "__module__"):
                    if ("algorithms" in newValue.__module__ or "dataModel" in newValue.__module__ or
                        "input" in newValue.__module__  or "util" in newValue.__module__ ):
                        count = True
                        if newValue not in knownObjects:
                            objectsThatNeedToBeDescribed.append(newValue)
            if count:
                string += " [see above or below]"
        string +="\n"


    for objToDescribe in objectsThatNeedToBeDescribed:
        #copyOfKnownObjects = copy.deepcopy(knownObjects)
        #copyOfKnownObjects.add(objToDescribe)
        copyOfKnownObjects = knownObjects
        copyOfKnownObjects.add(objToDescribe)
        subString, knownObjectsDepth = _prettyPrint(objToDescribe, indentOffset=indentOffset + indentStep, indentStep=indentStep, knownObjects=copyOfKnownObjects)
        knownObjects = knownObjects.union(knownObjectsDepth)
        string += subString

    return string, knownObjects

