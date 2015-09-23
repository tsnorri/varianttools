# This file was automatically generated by SWIG (http://www.swig.org).
# Version 3.0.2
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.





from sys import version_info
if version_info >= (3,0,0):
    new_instancemethod = lambda func, inst, cls: _cgatools.SWIG_PyInstanceMethod_New(func)
else:
    from new import instancemethod as new_instancemethod
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_cgatools', [dirname(__file__)])
        except ImportError:
            import _cgatools
            return _cgatools
        if fp is not None:
            try:
                _mod = imp.load_module('_cgatools', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _cgatools = swig_import_helper()
    del swig_import_helper
else:
    import _cgatools
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


def _swig_setattr_nondynamic_method(set):
    def set_attr(self,name,value):
        if (name == "thisown"): return self.this.own(value)
        if hasattr(self,name) or (name == "this"):
            set(self,name,value)
        else:
            raise AttributeError("You cannot add attributes to %s" % self)
    return set_attr


class SwigPyIterator(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    def __init__(self, *args, **kwargs): raise AttributeError("No constructor defined - class is abstract")
    __repr__ = _swig_repr
    __swig_destroy__ = _cgatools.delete_SwigPyIterator
    def __iter__(self): return self
SwigPyIterator.value = new_instancemethod(_cgatools.SwigPyIterator_value,None,SwigPyIterator)
SwigPyIterator.incr = new_instancemethod(_cgatools.SwigPyIterator_incr,None,SwigPyIterator)
SwigPyIterator.decr = new_instancemethod(_cgatools.SwigPyIterator_decr,None,SwigPyIterator)
SwigPyIterator.distance = new_instancemethod(_cgatools.SwigPyIterator_distance,None,SwigPyIterator)
SwigPyIterator.equal = new_instancemethod(_cgatools.SwigPyIterator_equal,None,SwigPyIterator)
SwigPyIterator.copy = new_instancemethod(_cgatools.SwigPyIterator_copy,None,SwigPyIterator)
SwigPyIterator.next = new_instancemethod(_cgatools.SwigPyIterator_next,None,SwigPyIterator)
SwigPyIterator.__next__ = new_instancemethod(_cgatools.SwigPyIterator___next__,None,SwigPyIterator)
SwigPyIterator.previous = new_instancemethod(_cgatools.SwigPyIterator_previous,None,SwigPyIterator)
SwigPyIterator.advance = new_instancemethod(_cgatools.SwigPyIterator_advance,None,SwigPyIterator)
SwigPyIterator.__eq__ = new_instancemethod(_cgatools.SwigPyIterator___eq__,None,SwigPyIterator)
SwigPyIterator.__ne__ = new_instancemethod(_cgatools.SwigPyIterator___ne__,None,SwigPyIterator)
SwigPyIterator.__iadd__ = new_instancemethod(_cgatools.SwigPyIterator___iadd__,None,SwigPyIterator)
SwigPyIterator.__isub__ = new_instancemethod(_cgatools.SwigPyIterator___isub__,None,SwigPyIterator)
SwigPyIterator.__add__ = new_instancemethod(_cgatools.SwigPyIterator___add__,None,SwigPyIterator)
SwigPyIterator.__sub__ = new_instancemethod(_cgatools.SwigPyIterator___sub__,None,SwigPyIterator)
SwigPyIterator_swigregister = _cgatools.SwigPyIterator_swigregister
SwigPyIterator_swigregister(SwigPyIterator)

CGATOOLS_UTIL_MD5_HPP_ = _cgatools.CGATOOLS_UTIL_MD5_HPP_
class Md5Digest(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        _cgatools.Md5Digest_swiginit(self,_cgatools.new_Md5Digest(*args, **kwargs))
    __swig_destroy__ = _cgatools.delete_Md5Digest
Md5Digest.set = new_instancemethod(_cgatools.Md5Digest_set,None,Md5Digest)
Md5Digest.data = new_instancemethod(_cgatools.Md5Digest_data,None,Md5Digest)
Md5Digest.size = new_instancemethod(_cgatools.Md5Digest_size,None,Md5Digest)
Md5Digest.hex = new_instancemethod(_cgatools.Md5Digest_hex,None,Md5Digest)
Md5Digest_swigregister = _cgatools.Md5Digest_swigregister
Md5Digest_swigregister(Md5Digest)

class Md5Context(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self): 
        _cgatools.Md5Context_swiginit(self,_cgatools.new_Md5Context())
    __swig_destroy__ = _cgatools.delete_Md5Context
Md5Context.init = new_instancemethod(_cgatools.Md5Context_init,None,Md5Context)
Md5Context.update = new_instancemethod(_cgatools.Md5Context_update,None,Md5Context)
Md5Context.getDigest = new_instancemethod(_cgatools.Md5Context_getDigest,None,Md5Context)
Md5Context.hexDigest = new_instancemethod(_cgatools.Md5Context_hexDigest,None,Md5Context)
Md5Context_swigregister = _cgatools.Md5Context_swigregister
Md5Context_swigregister(Md5Context)

CGATOOLS_REFERENCE_RANGE_HPP_ = _cgatools.CGATOOLS_REFERENCE_RANGE_HPP_
class Location(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        _cgatools.Location_swiginit(self,_cgatools.new_Location(*args, **kwargs))
    chromosome_ = _swig_property(_cgatools.Location_chromosome__get, _cgatools.Location_chromosome__set)
    offset_ = _swig_property(_cgatools.Location_offset__get, _cgatools.Location_offset__set)
    __swig_destroy__ = _cgatools.delete_Location
Location.distanceTo = new_instancemethod(_cgatools.Location_distanceTo,None,Location)
Location_swigregister = _cgatools.Location_swigregister
Location_swigregister(Location)


def __eq__(*args, **kwargs):
  return _cgatools.__eq__(*args, **kwargs)
__eq__ = _cgatools.__eq__

def __ne__(*args, **kwargs):
  return _cgatools.__ne__(*args, **kwargs)
__ne__ = _cgatools.__ne__

def __lt__(*args, **kwargs):
  return _cgatools.__lt__(*args, **kwargs)
__lt__ = _cgatools.__lt__

def __le__(*args, **kwargs):
  return _cgatools.__le__(*args, **kwargs)
__le__ = _cgatools.__le__

def __gt__(*args, **kwargs):
  return _cgatools.__gt__(*args, **kwargs)
__gt__ = _cgatools.__gt__

def __ge__(*args, **kwargs):
  return _cgatools.__ge__(*args, **kwargs)
__ge__ = _cgatools.__ge__

def __lshift__(*args, **kwargs):
  return _cgatools.__lshift__(*args, **kwargs)
__lshift__ = _cgatools.__lshift__
class Range(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        _cgatools.Range_swiginit(self,_cgatools.new_Range(*args, **kwargs))
    chromosome_ = _swig_property(_cgatools.Range_chromosome__get, _cgatools.Range_chromosome__set)
    begin_ = _swig_property(_cgatools.Range_begin__get, _cgatools.Range_begin__set)
    end_ = _swig_property(_cgatools.Range_end__get, _cgatools.Range_end__set)
    __swig_destroy__ = _cgatools.delete_Range
Range.beginLocation = new_instancemethod(_cgatools.Range_beginLocation,None,Range)
Range.endLocation = new_instancemethod(_cgatools.Range_endLocation,None,Range)
Range.length = new_instancemethod(_cgatools.Range_length,None,Range)
Range.contains = new_instancemethod(_cgatools.Range_contains,None,Range)
Range.intersects = new_instancemethod(_cgatools.Range_intersects,None,Range)
Range.overlappingRange = new_instancemethod(_cgatools.Range_overlappingRange,None,Range)
Range_swigregister = _cgatools.Range_swigregister
Range_swigregister(Range)

class RangeOverlap(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self): 
        _cgatools.RangeOverlap_swiginit(self,_cgatools.new_RangeOverlap())
    __swig_destroy__ = _cgatools.delete_RangeOverlap
RangeOverlap.__call__ = new_instancemethod(_cgatools.RangeOverlap___call__,None,RangeOverlap)
RangeOverlap_swigregister = _cgatools.RangeOverlap_swigregister
RangeOverlap_swigregister(RangeOverlap)

class GetRangeBoundary(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self): 
        _cgatools.GetRangeBoundary_swiginit(self,_cgatools.new_GetRangeBoundary())
    __swig_destroy__ = _cgatools.delete_GetRangeBoundary
GetRangeBoundary.__call__ = new_instancemethod(_cgatools.GetRangeBoundary___call__,None,GetRangeBoundary)
GetRangeBoundary_swigregister = _cgatools.GetRangeBoundary_swigregister
GetRangeBoundary_swigregister(GetRangeBoundary)

CGATOOLS_REFERENCE_COMPACTDNASEQUENCE_HPP_ = _cgatools.CGATOOLS_REFERENCE_COMPACTDNASEQUENCE_HPP_
class AmbiguousRegion(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        _cgatools.AmbiguousRegion_swiginit(self,_cgatools.new_AmbiguousRegion(*args, **kwargs))
    code_ = _swig_property(_cgatools.AmbiguousRegion_code__get, _cgatools.AmbiguousRegion_code__set)
    offset_ = _swig_property(_cgatools.AmbiguousRegion_offset__get, _cgatools.AmbiguousRegion_offset__set)
    length_ = _swig_property(_cgatools.AmbiguousRegion_length__get, _cgatools.AmbiguousRegion_length__set)
    __swig_destroy__ = _cgatools.delete_AmbiguousRegion
AmbiguousRegion_swigregister = _cgatools.AmbiguousRegion_swigregister
AmbiguousRegion_swigregister(AmbiguousRegion)

class CompactDnaSequence(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        _cgatools.CompactDnaSequence_swiginit(self,_cgatools.new_CompactDnaSequence(*args, **kwargs))
    __swig_destroy__ = _cgatools.delete_CompactDnaSequence
CompactDnaSequence.getSequence = new_instancemethod(_cgatools.CompactDnaSequence_getSequence,None,CompactDnaSequence)
CompactDnaSequence.getUnambiguousSequence = new_instancemethod(_cgatools.CompactDnaSequence_getUnambiguousSequence,None,CompactDnaSequence)
CompactDnaSequence.appendSequence = new_instancemethod(_cgatools.CompactDnaSequence_appendSequence,None,CompactDnaSequence)
CompactDnaSequence.appendUnambiguousSequence = new_instancemethod(_cgatools.CompactDnaSequence_appendUnambiguousSequence,None,CompactDnaSequence)
CompactDnaSequence.getBase = new_instancemethod(_cgatools.CompactDnaSequence_getBase,None,CompactDnaSequence)
CompactDnaSequence.getUnambiguousBase = new_instancemethod(_cgatools.CompactDnaSequence_getUnambiguousBase,None,CompactDnaSequence)
CompactDnaSequence.extendLeftBy3Mers = new_instancemethod(_cgatools.CompactDnaSequence_extendLeftBy3Mers,None,CompactDnaSequence)
CompactDnaSequence.extendRightBy3Mers = new_instancemethod(_cgatools.CompactDnaSequence_extendRightBy3Mers,None,CompactDnaSequence)
CompactDnaSequence.validate = new_instancemethod(_cgatools.CompactDnaSequence_validate,None,CompactDnaSequence)
CompactDnaSequence.getName = new_instancemethod(_cgatools.CompactDnaSequence_getName,None,CompactDnaSequence)
CompactDnaSequence.isCircular = new_instancemethod(_cgatools.CompactDnaSequence_isCircular,None,CompactDnaSequence)
CompactDnaSequence.getMd5Digest = new_instancemethod(_cgatools.CompactDnaSequence_getMd5Digest,None,CompactDnaSequence)
CompactDnaSequence.length = new_instancemethod(_cgatools.CompactDnaSequence_length,None,CompactDnaSequence)
CompactDnaSequence.getAmbiguousRegions = new_instancemethod(_cgatools.CompactDnaSequence_getAmbiguousRegions,None,CompactDnaSequence)
CompactDnaSequence_swigregister = _cgatools.CompactDnaSequence_swigregister
CompactDnaSequence_swigregister(CompactDnaSequence)

CGATOOLS_REFERENCE_CRRFILE_HPP_ = _cgatools.CGATOOLS_REFERENCE_CRRFILE_HPP_
class CrrFile(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        _cgatools.CrrFile_swiginit(self,_cgatools.new_CrrFile(*args, **kwargs))
    currentVersion = staticmethod(_cgatools.CrrFile_currentVersion)
    __swig_destroy__ = _cgatools.delete_CrrFile
CrrFile.open = new_instancemethod(_cgatools.CrrFile_open,None,CrrFile)
CrrFile.listChromosomes = new_instancemethod(_cgatools.CrrFile_listChromosomes,None,CrrFile)
CrrFile.listContigs = new_instancemethod(_cgatools.CrrFile_listContigs,None,CrrFile)
CrrFile.getSequence = new_instancemethod(_cgatools.CrrFile_getSequence,None,CrrFile)
CrrFile.getBase = new_instancemethod(_cgatools.CrrFile_getBase,None,CrrFile)
CrrFile.getChromosomeId = new_instancemethod(_cgatools.CrrFile_getChromosomeId,None,CrrFile)
CrrFile.validate = new_instancemethod(_cgatools.CrrFile_validate,None,CrrFile)
CrrFile.getLocation = new_instancemethod(_cgatools.CrrFile_getLocation,None,CrrFile)
CrrFile_swigregister = _cgatools.CrrFile_swigregister
CrrFile_swigregister(CrrFile)

def CrrFile_currentVersion():
  return _cgatools.CrrFile_currentVersion()
CrrFile_currentVersion = _cgatools.CrrFile_currentVersion


def parseFastaHeader(*args, **kwargs):
  return _cgatools.parseFastaHeader(*args, **kwargs)
parseFastaHeader = _cgatools.parseFastaHeader

def fasta2crr(*args, **kwargs):
  return _cgatools.fasta2crr(*args, **kwargs)
fasta2crr = _cgatools.fasta2crr


