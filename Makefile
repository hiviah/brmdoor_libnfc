DEFAULT_PYTHON_VERSION := $(shell python2 -c 'import platform; print "%s.%s" % platform.python_version_tuple()[:2]')
PYTHON_CONFIG := python$(DEFAULT_PYTHON_VERSION)-config
PYTHON_INCLUDES := $(shell $(PYTHON_CONFIG) --includes)
CXXFLAGS += -Wall -g $(PYTHON_INCLUDES) -fPIC -std=c++11
LDFLAGS += -lnfc -lfreefare
OBJECTS = nfc_smartcard.o nfc_smartcard_wrap.o
SWIG_GENERATED = nfc_smartcard_wrap.cxx nfc_smartcard.py
PY_MODULE = _nfc_smartcard.so

all: $(PY_MODULE)

$(PY_MODULE): $(OBJECTS)
	g++ -shared -o $@ $(OBJECTS) $(LDFLAGS)

nfc_smartcard.o: nfc_smartcard.cpp nfc_smartcard.h
	g++ -c $(CXXFLAGS) nfc_smartcard.cpp

nfc_smartcard_wrap.o: nfc_smartcard_wrap.cxx
	g++ -c $(CXXFLAGS) $<

nfc_smartcard_wrap.cxx: nfc_smartcard.i nfc_smartcard.h
	swig3.0 -python -c++ $<

clean:
	rm -f $(OBJECTS) $(PY_MODULE) $(SWIG_GENERATED) *.pyc

doxygen:
	doxygen Doxyfile
